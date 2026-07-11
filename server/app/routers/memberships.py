from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Membership, MembershipStatus
from app.schemas.membership import MembershipCreate, MembershipRead
from app.services.memberships import change_status, create_membership, serialize_membership, unfreeze

router = APIRouter(prefix="/memberships", tags=["memberships"])


@router.get("", response_model=list[MembershipRead])
def list_memberships(status: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Membership).options(joinedload(Membership.participant), joinedload(Membership.membership_type))
    if status:
        query = query.filter(Membership.status == MembershipStatus(status))
    memberships = query.order_by(Membership.created_at.desc()).all()
    result = [serialize_membership(db, membership) for membership in memberships]
    db.commit()
    return result


@router.get("/{membership_id}", response_model=MembershipRead)
def get_membership(membership_id: int, db: Session = Depends(get_db)):
    membership = (
        db.query(Membership)
        .options(joinedload(Membership.participant), joinedload(Membership.membership_type))
        .filter(Membership.id == membership_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    result = serialize_membership(db, membership)
    db.commit()
    return result


@router.post("", response_model=MembershipRead)
def post_membership(payload: MembershipCreate, db: Session = Depends(get_db)):
    membership = create_membership(db, payload.participant_id, payload.membership_type_id)
    return get_membership(membership.id, db)


@router.post("/{membership_id}/freeze", response_model=MembershipRead)
def freeze_membership(membership_id: int, db: Session = Depends(get_db)):
    membership = change_status(db, membership_id, MembershipStatus.FROZEN)
    return get_membership(membership.id, db)


@router.post("/{membership_id}/unfreeze", response_model=MembershipRead)
def unfreeze_membership(membership_id: int, db: Session = Depends(get_db)):
    membership = unfreeze(db, membership_id)
    return get_membership(membership.id, db)


@router.post("/{membership_id}/cancel", response_model=MembershipRead)
def cancel_membership(membership_id: int, db: Session = Depends(get_db)):
    membership = change_status(db, membership_id, MembershipStatus.CANCELLED)
    return get_membership(membership.id, db)

