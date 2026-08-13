from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Operator, PracticeRentalStatus, PracticeTariff
from app.schemas.practice import (
    PracticeRentalCreate,
    PracticeRentalRead,
    PracticeRentalSummary,
    PracticeTariffCreate,
    PracticeTariffRead,
    PracticeTariffUpdate,
)
from app.services.audit import log_action, snapshot
from app.services.auth import get_current_operator, require_admin, require_operator_access
from app.services.practice import (
    cancel_practice_rental,
    create_practice_rental,
    create_practice_tariff,
    get_practice_summary,
    list_practice_rentals,
    list_practice_tariffs,
    serialize_practice_rental,
    update_practice_tariff,
)

router = APIRouter(tags=["practice"])


@router.get("/practice-tariffs", response_model=list[PracticeTariffRead])
def tariffs(active_only: bool = Query(default=False), db: Session = Depends(get_db), _operator: Operator = Depends(get_current_operator)):
    return list_practice_tariffs(db, active_only=active_only)


@router.post("/practice-tariffs", response_model=PracticeTariffRead)
def create_tariff(payload: PracticeTariffCreate, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    tariff = create_practice_tariff(db, payload.model_dump())
    log_action(db, operator, "practice_tariff_created", "practice_tariff", tariff.id, tariff.name, after=snapshot(tariff, ["name", "price", "is_active", "sort_order"]))
    return tariff


@router.patch("/practice-tariffs/{tariff_id}", response_model=PracticeTariffRead)
def patch_tariff(tariff_id: int, payload: PracticeTariffUpdate, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    current = db.get(PracticeTariff, tariff_id)
    before = snapshot(current, ["name", "price", "is_active", "sort_order"]) if current else None
    tariff = update_practice_tariff(db, tariff_id, payload.model_dump(exclude_unset=True))
    log_action(db, operator, "practice_tariff_updated", "practice_tariff", tariff.id, tariff.name, before=before, after=snapshot(tariff, ["name", "price", "is_active", "sort_order"]))
    return tariff


@router.get("/practice-rentals", response_model=list[PracticeRentalRead])
def rentals(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None),
    tariff_id: int | None = Query(default=None),
    status: PracticeRentalStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _operator: Operator = Depends(get_current_operator),
):
    return list_practice_rentals(db, date_from, date_to, search, tariff_id, status, page, page_size)


@router.get("/practice-rentals/summary", response_model=PracticeRentalSummary)
def rentals_summary(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _operator: Operator = Depends(get_current_operator),
):
    return get_practice_summary(db, date_from, date_to)


@router.post("/practice-rentals", response_model=PracticeRentalRead)
def create_rental(payload: PracticeRentalCreate, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    rental = create_practice_rental(db, payload, operator)
    log_action(db, operator, "practice_rental_created", "practice_rental", rental.id, rental.customer_name, after={"amount": str(rental.amount), "tariff": rental.tariff_name_snapshot})
    return serialize_practice_rental(rental)


@router.post("/practice-rentals/{rental_id}/cancel", response_model=PracticeRentalRead)
def cancel_rental(rental_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    rental = cancel_practice_rental(db, rental_id, operator)
    log_action(db, operator, "practice_rental_cancelled", "practice_rental", rental.id, rental.customer_name, after=snapshot(rental, ["status", "cancelled_at", "cancelled_by_user_id"]))
    return serialize_practice_rental(rental)
