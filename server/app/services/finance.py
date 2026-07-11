from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import Membership, Payment, Teacher, Visit
from app.services.lesson_finance import MONEY, ensure_visit_financials, quantize_money, quantize_percent


def get_teacher_earnings(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    teacher_id: int | None = None,
    include_cancelled: bool = False,
) -> list[dict]:
    teachers_query = db.query(Teacher).order_by(Teacher.full_name)
    if teacher_id:
        teachers_query = teachers_query.filter(Teacher.id == teacher_id)
    teachers = teachers_query.all()

    query = (
        db.query(Visit)
        .options(
            joinedload(Visit.teacher),
            joinedload(Visit.participant),
            joinedload(Visit.membership).joinedload(Membership.membership_type),
        )
    )
    if date_from:
        query = query.filter(Visit.visit_date >= date_from)
    if date_to:
        query = query.filter(Visit.visit_date <= date_to)
    if teacher_id:
        query = query.filter(Visit.teacher_id == teacher_id)
    if not include_cancelled:
        query = query.filter(Visit.is_cancelled.is_(False))

    visits = query.order_by(Visit.visit_date.desc(), Visit.id.desc()).all()
    valid_visits = []
    for visit in visits:
        try:
            ensure_visit_financials(visit)
        except HTTPException:
            continue
        db.add(visit)
        valid_visits.append(visit)
    db.commit()
    visits = valid_visits

    total_teacher_payouts = sum(
        (Decimal(visit.teacher_earning or 0) for visit in visits if not visit.is_cancelled),
        Decimal("0"),
    )

    earnings: dict[int, dict] = {
        teacher.id: {
            "teacher_id": teacher.id,
            "teacher_name": teacher.full_name,
            "teacher_share_percent": quantize_percent(Decimal(teacher.teacher_share_percent)),
            "visits_count": 0,
            "completed_lessons_value": Decimal("0"),
            "teacher_earned": Decimal("0"),
            "school_earned": Decimal("0"),
            "average_lesson_price": Decimal("0"),
            "average_teacher_earning": Decimal("0"),
            "share_of_total_teacher_payouts": Decimal("0"),
            "last_visit_date": None,
            "visits": [],
        }
        for teacher in teachers
    }

    for visit in visits:
        if visit.teacher_id not in earnings:
            continue
        item = earnings[visit.teacher_id]
        lesson_price = quantize_money(Decimal(visit.lesson_price or 0))
        teacher_earning = quantize_money(Decimal(visit.teacher_earning or 0))
        school_earning = quantize_money(Decimal(visit.school_earning or 0))
        item["visits"].append(
            {
                "visit_id": visit.id,
                "visit_date": visit.visit_date,
                "participant_id": visit.participant_id,
                "participant_name": visit.participant.full_name if visit.participant else "—",
                "membership_id": visit.membership_id,
                "membership_name": visit.membership.membership_type.name if visit.membership and visit.membership.membership_type else f"Абонемент #{visit.membership_id}",
                "lesson_price": lesson_price,
                "teacher_share_percent": quantize_percent(Decimal(visit.teacher_share_percent or 0)),
                "teacher_earning": teacher_earning,
                "school_earning": school_earning,
                "is_cancelled": visit.is_cancelled,
            }
        )
        if visit.is_cancelled:
            continue
        item["visits_count"] += 1
        item["completed_lessons_value"] += lesson_price
        item["teacher_earned"] += teacher_earning
        item["school_earned"] += school_earning
        if item["last_visit_date"] is None or visit.visit_date > item["last_visit_date"]:
            item["last_visit_date"] = visit.visit_date

    for item in earnings.values():
        visits_count = item["visits_count"]
        item["completed_lessons_value"] = quantize_money(item["completed_lessons_value"])
        item["teacher_earned"] = quantize_money(item["teacher_earned"])
        item["school_earned"] = quantize_money(item["school_earned"])
        item["average_lesson_price"] = quantize_money(item["completed_lessons_value"] / Decimal(visits_count)) if visits_count else Decimal("0.00")
        item["average_teacher_earning"] = quantize_money(item["teacher_earned"] / Decimal(visits_count)) if visits_count else Decimal("0.00")
        item["share_of_total_teacher_payouts"] = (
            quantize_percent(item["teacher_earned"] * Decimal("100") / total_teacher_payouts)
            if total_teacher_payouts
            else Decimal("0.00")
        )

    return sorted(
        earnings.values(),
        key=lambda item: (item["last_visit_date"] or date.min, item["teacher_earned"], item["teacher_name"]),
        reverse=True,
    )


def get_summary(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    teacher_id: int | None = None,
) -> dict:
    teacher_membership_ids: list[int] | None = None
    if teacher_id:
        teacher_membership_query = db.query(Visit.membership_id).filter(
            Visit.teacher_id == teacher_id,
            Visit.is_cancelled.is_(False),
        )
        if date_from:
            teacher_membership_query = teacher_membership_query.filter(Visit.visit_date >= date_from)
        if date_to:
            teacher_membership_query = teacher_membership_query.filter(Visit.visit_date <= date_to)
        teacher_membership_ids = [row[0] for row in teacher_membership_query.distinct().all()]

    memberships_query = db.query(func.coalesce(func.sum(Membership.price), 0))
    if date_from:
        memberships_query = memberships_query.filter(Membership.start_date >= date_from)
    if date_to:
        memberships_query = memberships_query.filter(Membership.start_date <= date_to)
    if teacher_membership_ids is not None:
        memberships_query = memberships_query.filter(Membership.id.in_(teacher_membership_ids))
    memberships_sold_total = Decimal(memberships_query.scalar() or 0)

    payments_query = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.is_cancelled.is_(False))
    if date_from:
        payments_query = payments_query.filter(Payment.payment_date >= date_from)
    if date_to:
        payments_query = payments_query.filter(Payment.payment_date <= date_to)
    if teacher_membership_ids is not None:
        payments_query = payments_query.filter(Payment.membership_id.in_(teacher_membership_ids))
    payments_received_total = Decimal(payments_query.scalar() or 0)

    visit_query = db.query(Visit).filter(Visit.is_cancelled.is_(False))
    if date_from:
        visit_query = visit_query.filter(Visit.visit_date >= date_from)
    if date_to:
        visit_query = visit_query.filter(Visit.visit_date <= date_to)
    if teacher_id:
        visit_query = visit_query.filter(Visit.teacher_id == teacher_id)
    visits = visit_query.options(joinedload(Visit.teacher), joinedload(Visit.membership)).all()
    valid_visits = []
    for visit in visits:
        try:
            ensure_visit_financials(visit)
        except HTTPException:
            continue
        db.add(visit)
        valid_visits.append(visit)
    db.commit()
    visits = valid_visits

    completed_lessons_value = sum((Decimal(visit.lesson_price or 0) for visit in visits), Decimal("0"))
    teacher_earnings_total = sum((Decimal(visit.teacher_earning or 0) for visit in visits), Decimal("0"))
    school_earnings_total = sum((Decimal(visit.school_earning or 0) for visit in visits), Decimal("0"))
    completed_visits_count = len(visits)
    active_teachers_query = db.query(Teacher).filter(Teacher.is_active.is_(True))
    if teacher_id:
        active_teachers_query = active_teachers_query.filter(Teacher.id == teacher_id)
    active_teachers_count = active_teachers_query.count()

    return {
        "memberships_sold_total": quantize_money(memberships_sold_total),
        "payments_received_total": quantize_money(payments_received_total),
        "completed_lessons_value": quantize_money(completed_lessons_value),
        "teacher_earnings_total": quantize_money(teacher_earnings_total),
        "school_earnings_total": quantize_money(school_earnings_total),
        "completed_visits_count": completed_visits_count,
        "average_lesson_price": quantize_money(completed_lessons_value / Decimal(completed_visits_count)) if completed_visits_count else Decimal("0.00"),
        "average_teacher_earning": quantize_money(teacher_earnings_total / Decimal(completed_visits_count)) if completed_visits_count else Decimal("0.00"),
        "active_teachers_count": active_teachers_count,
    }


def ensure_teacher_seed(db: Session) -> list[Teacher]:
    if db.query(Teacher).count() == 0:
        db.add_all(
            [
                Teacher(full_name="София Белова", phone="+7 901 100-10-10", comment="Сальса и бачата", teacher_share_percent=Decimal("50")),
                Teacher(full_name="Марк Волков", phone="+7 901 200-20-20", comment="Групповые занятия", teacher_share_percent=Decimal("50")),
                Teacher(full_name="Виктория Лебедева", phone="+7 901 300-30-30", comment="Индивидуальные занятия", teacher_share_percent=Decimal("50")),
            ]
        )
        db.commit()
    return db.query(Teacher).order_by(Teacher.id).all()
