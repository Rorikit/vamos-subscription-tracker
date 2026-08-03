import logging
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import Membership, Visit

MONEY = Decimal("0.01")
PERCENT = Decimal("0.01")
logger = logging.getLogger(__name__)


def quantize_money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY)


def quantize_percent(value: Decimal) -> Decimal:
    return Decimal(value).quantize(PERCENT)


def calculate_visit_financials(membership: Membership) -> dict[str, Decimal]:
    if membership.total_lessons <= 0:
        raise HTTPException(status_code=400, detail="В абонементе некорректное количество занятий")

    lesson_price = quantize_money(Decimal(membership.price) / Decimal(membership.total_lessons))
    teacher_lesson_rate = quantize_money(Decimal(membership.teacher_lesson_rate or 0))
    if teacher_lesson_rate < 0:
        raise HTTPException(status_code=400, detail="Выплата преподавателю не может быть отрицательной")
    if teacher_lesson_rate > lesson_price:
        raise HTTPException(status_code=400, detail="Выплата преподавателю не может быть больше цены занятия")

    teacher_earning = teacher_lesson_rate
    school_earning = quantize_money(lesson_price - teacher_earning)
    return {
        "lesson_price": lesson_price,
        "teacher_lesson_rate": teacher_lesson_rate,
        "teacher_share_percent": quantize_percent(teacher_lesson_rate * Decimal("100") / lesson_price) if lesson_price else Decimal("0.00"),
        "teacher_earning": teacher_earning,
        "school_earning": school_earning,
    }


def ensure_visit_financials(visit: Visit) -> None:
    if (
        visit.lesson_price is not None
        and visit.teacher_lesson_rate is not None
        and visit.teacher_share_percent is not None
        and visit.teacher_earning is not None
        and visit.school_earning is not None
    ):
        return
    if not visit.membership or not visit.teacher:
        return
    values = calculate_visit_financials(visit.membership)
    visit.lesson_price = values["lesson_price"]
    visit.teacher_lesson_rate = values["teacher_lesson_rate"]
    visit.teacher_share_percent = values["teacher_share_percent"]
    visit.teacher_earning = values["teacher_earning"]
    visit.school_earning = values["school_earning"]


def backfill_visit_financials(db: Session) -> int:
    visits = (
        db.query(Visit)
        .options(joinedload(Visit.teacher), joinedload(Visit.membership))
        .filter(
            (Visit.lesson_price.is_(None))
            | (Visit.teacher_lesson_rate.is_(None))
            | (Visit.teacher_share_percent.is_(None))
            | (Visit.teacher_earning.is_(None))
            | (Visit.school_earning.is_(None))
        )
        .all()
    )
    updated = 0
    for visit in visits:
        before = (visit.lesson_price, visit.teacher_lesson_rate, visit.teacher_share_percent, visit.teacher_earning, visit.school_earning)
        try:
            ensure_visit_financials(visit)
        except HTTPException as exc:
            logger.warning("Skipping visit %s financial backfill: %s", visit.id, exc.detail)
            continue
        after = (visit.lesson_price, visit.teacher_lesson_rate, visit.teacher_share_percent, visit.teacher_earning, visit.school_earning)
        if after != before:
            updated += 1
            db.add(visit)
    db.commit()
    return updated
