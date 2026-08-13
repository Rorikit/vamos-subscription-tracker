from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import Operator, PracticeRental, PracticeRentalStatus, PracticeTariff, Teacher
from app.schemas.practice import PracticeRentalCreate
from app.services.lesson_finance import quantize_money

DEFAULT_PRACTICE_TARIFFS = [
    {"name": "Практика — 300 ₽", "price": Decimal("300.00"), "sort_order": 10},
    {"name": "Практика — 500 ₽", "price": Decimal("500.00"), "sort_order": 20},
]


def ensure_practice_tariffs(db: Session) -> list[PracticeTariff]:
    for item in DEFAULT_PRACTICE_TARIFFS:
        exists = (
            db.query(PracticeTariff)
            .filter(PracticeTariff.name == item["name"], PracticeTariff.price == item["price"])
            .first()
        )
        if not exists:
            db.add(PracticeTariff(name=item["name"], price=item["price"], is_active=True, sort_order=item["sort_order"]))
    db.commit()
    return list_practice_tariffs(db)


def list_practice_tariffs(db: Session, active_only: bool = False) -> list[PracticeTariff]:
    query = db.query(PracticeTariff)
    if active_only:
        query = query.filter(PracticeTariff.is_active.is_(True))
    return query.order_by(PracticeTariff.sort_order, PracticeTariff.price, PracticeTariff.name).all()


def create_practice_tariff(db: Session, data: dict) -> PracticeTariff:
    tariff = PracticeTariff(**data)
    db.add(tariff)
    db.commit()
    db.refresh(tariff)
    return tariff


def update_practice_tariff(db: Session, tariff_id: int, data: dict) -> PracticeTariff:
    tariff = db.get(PracticeTariff, tariff_id)
    if not tariff:
        raise HTTPException(status_code=404, detail="Тариф практики не найден")
    for key, value in data.items():
        setattr(tariff, key, value)
    db.add(tariff)
    db.commit()
    db.refresh(tariff)
    return tariff


def create_practice_rental(db: Session, payload: PracticeRentalCreate, operator: Operator) -> PracticeRental:
    tariff = db.get(PracticeTariff, payload.tariff_id)
    if not tariff:
        raise HTTPException(status_code=404, detail="Тариф практики не найден")
    if not tariff.is_active:
        raise HTTPException(status_code=400, detail="Нельзя использовать отключенный тариф практики")

    teacher: Teacher | None = None
    customer_name = payload.customer_name.strip()
    if payload.registered_teacher_id is not None:
        teacher = db.get(Teacher, payload.registered_teacher_id)
        if not teacher:
            raise HTTPException(status_code=404, detail="Преподаватель не найден")
        customer_name = teacher.full_name.strip()

    if not customer_name:
        raise HTTPException(status_code=400, detail="Укажите арендатора практики")

    rental = PracticeRental(
        registered_teacher_id=teacher.id if teacher else None,
        customer_name=customer_name,
        tariff_id=tariff.id,
        tariff_name_snapshot=tariff.name,
        amount=quantize_money(Decimal(tariff.price)),
        practiced_at=payload.practiced_at,
        status=PracticeRentalStatus.ACTIVE,
        comment=payload.comment,
        created_by_user_id=operator.id,
    )
    db.add(rental)
    db.commit()
    db.refresh(rental)
    return rental


def cancel_practice_rental(db: Session, rental_id: int, operator: Operator) -> PracticeRental:
    rental = db.get(PracticeRental, rental_id)
    if not rental:
        raise HTTPException(status_code=404, detail="Запись практики не найдена")
    if rental.status == PracticeRentalStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Практика уже отменена")
    rental.status = PracticeRentalStatus.CANCELLED
    rental.cancelled_at = datetime.utcnow()
    rental.cancelled_by_user_id = operator.id
    db.add(rental)
    db.commit()
    db.refresh(rental)
    return rental


def list_practice_rentals(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    tariff_id: int | None = None,
    status_filter: PracticeRentalStatus | None = None,
    page: int = 1,
    page_size: int = 100,
) -> list[dict]:
    query = _filtered_rentals_query(db, date_from, date_to, tariff_id, status_filter)
    rentals = query.order_by(PracticeRental.practiced_at.desc(), PracticeRental.id.desc()).all()
    if search:
        needle = search.strip().casefold()
        rentals = [
            rental
            for rental in rentals
            if needle in rental.customer_name.casefold()
            or (rental.registered_teacher and needle in rental.registered_teacher.full_name.casefold())
        ]
    page_size = min(max(page_size, 1), 200)
    offset = (max(page, 1) - 1) * page_size
    rentals = rentals[offset : offset + page_size]
    return [serialize_practice_rental(rental) for rental in rentals]


def get_practice_summary(db: Session, date_from: date | None = None, date_to: date | None = None) -> dict:
    query = db.query(PracticeRental).filter(PracticeRental.status == PracticeRentalStatus.ACTIVE)
    query = _apply_date_range(query, date_from, date_to)
    rows = query.all()
    total = quantize_money(sum((Decimal(row.amount or 0) for row in rows), Decimal("0")))
    count = len(rows)
    return {
        "income_total": total,
        "rentals_count": count,
        "average_check": quantize_money(total / Decimal(count)) if count else Decimal("0.00"),
    }


def get_practice_income(db: Session, date_from: date | None = None, date_to: date | None = None) -> Decimal:
    query = db.query(func.coalesce(func.sum(PracticeRental.amount), 0)).filter(PracticeRental.status == PracticeRentalStatus.ACTIVE)
    query = _apply_date_range(query, date_from, date_to)
    return quantize_money(Decimal(query.scalar() or 0))


def serialize_practice_rental(rental: PracticeRental) -> dict:
    return {
        "id": rental.id,
        "registered_teacher_id": rental.registered_teacher_id,
        "customer_name": rental.customer_name,
        "tariff_id": rental.tariff_id,
        "tariff_name_snapshot": rental.tariff_name_snapshot,
        "amount": quantize_money(Decimal(rental.amount or 0)),
        "practiced_at": rental.practiced_at,
        "status": rental.status,
        "comment": rental.comment,
        "created_by_user_id": rental.created_by_user_id,
        "created_by_name": rental.created_by.full_name if rental.created_by else None,
        "cancelled_at": rental.cancelled_at,
        "cancelled_by_user_id": rental.cancelled_by_user_id,
        "created_at": rental.created_at,
        "updated_at": rental.updated_at,
    }


def _filtered_rentals_query(
    db: Session,
    date_from: date | None,
    date_to: date | None,
    tariff_id: int | None,
    status_filter: PracticeRentalStatus | None,
):
    query = db.query(PracticeRental).options(joinedload(PracticeRental.created_by), joinedload(PracticeRental.tariff), joinedload(PracticeRental.registered_teacher))
    query = _apply_date_range(query, date_from, date_to)
    if tariff_id:
        query = query.filter(PracticeRental.tariff_id == tariff_id)
    if status_filter:
        query = query.filter(PracticeRental.status == status_filter)
    return query


def _apply_date_range(query, date_from: date | None, date_to: date | None):
    if date_from:
        query = query.filter(PracticeRental.practiced_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(PracticeRental.practiced_at < datetime.combine(date_to + timedelta(days=1), time.min))
    return query
