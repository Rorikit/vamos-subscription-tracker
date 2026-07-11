from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MembershipType
from app.schemas.membership_type import MembershipTypeCreate, MembershipTypeRead, MembershipTypeUpdate

router = APIRouter(prefix="/membership-types", tags=["membership-types"])


@router.get("", response_model=list[MembershipTypeRead])
def list_membership_types(db: Session = Depends(get_db)):
    return db.query(MembershipType).order_by(MembershipType.id).all()


@router.post("", response_model=MembershipTypeRead)
def create_membership_type(payload: MembershipTypeCreate, db: Session = Depends(get_db)):
    membership_type = MembershipType(**payload.model_dump())
    db.add(membership_type)
    db.commit()
    db.refresh(membership_type)
    return membership_type


@router.patch("/{membership_type_id}", response_model=MembershipTypeRead)
def update_membership_type(membership_type_id: int, payload: MembershipTypeUpdate, db: Session = Depends(get_db)):
    membership_type = db.get(MembershipType, membership_type_id)
    if not membership_type:
        raise HTTPException(status_code=404, detail="Тип абонемента не найден")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(membership_type, key, value)
    db.add(membership_type)
    db.commit()
    db.refresh(membership_type)
    return membership_type

