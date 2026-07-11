from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import Membership, Payment, Teacher, Visit

MONEY = Decimal("0.01")


def get_teacher_earnings(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    teacher_id: int | None = None,
) -> list[dict]:
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

    earnings: dict[int, dict] = {}
    for visit in query.all():
        if not visit.teacher or not visit.membership or visit.membership.total_lessons <= 0:
            continue
        lesson_price = (Decimal(visit.membership.price) / Decimal(visit.membership.total_lessons)).quantize(MONEY)
        item = earnings.setdefault(
            visit.teacher_id,
            {
                "teacher_id": visit.teacher_id,
                "teacher_name": visit.teacher.full_name,
                "visits_count": 0,
                "total_earned": Decimal("0"),
                "average_lesson_price": Decimal("0"),
                "visits": [],
            },
        )
        item["visits"].append(
            {
                "visit_id": visit.id,
                "visit_date": visit.visit_date,
                "participant_id": visit.participant_id,
                "participant_name": visit.participant.full_name if visit.participant else "—",
                "membership_id": visit.membership_id,
                "membership_name": visit.membership.membership_type.name if visit.membership.membership_type else f"Абонемент #{visit.membership_id}",
                "lesson_price": lesson_price,
                "is_cancelled": visit.is_cancelled,
            }
        )
        if not visit.is_cancelled:
            item["visits_count"] += 1
            item["total_earned"] += lesson_price

    for item in earnings.values():
        item["total_earned"] = Decimal(item["total_earned"]).quantize(MONEY)
        item["average_lesson_price"] = (
            (item["total_earned"] / Decimal(item["visits_count"])).quantize(MONEY) if item["visits_count"] else Decimal("0")
        )
        item["visits"].sort(key=lambda visit: (visit["visit_date"], visit["visit_id"]), reverse=True)

    return sorted(earnings.values(), key=lambda item: item["total_earned"], reverse=True)


def get_summary(db: Session) -> dict:
    total_revenue = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.is_cancelled.is_(False))
        .scalar()
    )
    total_visits = db.query(Visit).filter(Visit.is_cancelled.is_(False)).count()
    teacher_earnings = get_teacher_earnings(db)
    teacher_earnings_total = sum((item["total_earned"] for item in teacher_earnings), Decimal("0"))
    return {
        "total_revenue": Decimal(total_revenue or 0),
        "total_visits": total_visits,
        "teacher_earnings_total": teacher_earnings_total,
        "teacher_earnings": teacher_earnings,
    }


def ensure_teacher_seed(db: Session) -> list[Teacher]:
    if db.query(Teacher).count() == 0:
        db.add_all(
            [
                Teacher(full_name="София Белова", phone="+7 901 100-10-10", comment="Сальса и бачата"),
                Teacher(full_name="Марк Волков", phone="+7 901 200-20-20", comment="Групповые занятия"),
                Teacher(full_name="Виктория Лебедева", phone="+7 901 300-30-30", comment="Индивидуальные занятия"),
            ]
        )
        db.commit()
    return db.query(Teacher).order_by(Teacher.id).all()
