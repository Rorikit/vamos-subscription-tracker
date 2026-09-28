from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MembershipType, Operator
from app.schemas.membership_type import MembershipTypeCreate, MembershipTypeRead, MembershipTypeUpdate
from app.services.audit import log_action, snapshot
from app.services.auth import require_admin

router = APIRouter(prefix="/membership-types", tags=["membership-types"])


@router.get("", response_model=list[MembershipTypeRead])
def list_membership_types(db: Session = Depends(get_db)):
    return db.query(MembershipType).order_by(MembershipType.id).all()


@router.post("", response_model=MembershipTypeRead)
def create_membership_type(payload: MembershipTypeCreate, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    membership_type = MembershipType(**payload.model_dump())
    db.add(membership_type)
    db.commit()
    db.refresh(membership_type)
    log_action(db, operator, "membership_type_created", "membership_type", membership_type.id, membership_type.name, after=snapshot(membership_type, ["name", "lesson_count", "price", "validity_days", "is_active"]))
    return membership_type


@router.patch("/{membership_type_id}", response_model=MembershipTypeRead)
def update_membership_type(membership_type_id: int, payload: MembershipTypeUpdate, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    membership_type = db.get(MembershipType, membership_type_id)
    if not membership_type:
        raise HTTPException(status_code=404, detail="Тип абонемента не найден")
    before = snapshot(membership_type, ["name", "lesson_count", "price", "validity_days", "description", "is_active"])
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(membership_type, key, value)
    cash_price = membership_type.cash_price if membership_type.cash_price is not None else membership_type.price
    card_price = membership_type.card_price if membership_type.card_price is not None else membership_type.price
    if cash_price <= 0 or card_price <= 0 or card_price < cash_price:
        raise HTTPException(status_code=400, detail="Цена картой должна быть не ниже цены наличными, обе цены должны быть больше нуля")
    membership_type.cash_price = cash_price
    membership_type.card_price = card_price
    membership_type.price = cash_price
    db.add(membership_type)
    db.commit()
    db.refresh(membership_type)
    log_action(db, operator, "membership_type_updated", "membership_type", membership_type.id, membership_type.name, before=before, after=snapshot(membership_type, ["name", "lesson_count", "price", "validity_days", "description", "is_active"]))
    return membership_type
