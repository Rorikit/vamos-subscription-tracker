from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Membership, MembershipChange, MembershipRevision, MembershipStatus, Operator
from app.schemas.membership_finance import MembershipChangeRead, MembershipRevisionRead
from app.schemas.membership import MembershipCreate, MembershipRead, MembershipReplace, MembershipUpdate
from app.services.audit import log_action, snapshot
from app.services.auth import require_admin, require_operator_access
from app.services.memberships import change_status, create_membership, replace_membership, serialize_membership, unfreeze, update_membership

router = APIRouter(prefix="/memberships", tags=["memberships"])


@router.get("/{membership_id}/revisions", response_model=list[MembershipRevisionRead])
def list_membership_revisions(membership_id: int, db: Session = Depends(get_db)):
    if not db.get(Membership, membership_id):
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    return db.query(MembershipRevision).filter(MembershipRevision.membership_id == membership_id).order_by(MembershipRevision.revision_number).all()


@router.get("/{membership_id}/changes", response_model=list[MembershipChangeRead])
def list_membership_changes(membership_id: int, db: Session = Depends(get_db)):
    if not db.get(Membership, membership_id):
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    return (
        db.query(MembershipChange)
        .filter((MembershipChange.old_membership_id == membership_id) | (MembershipChange.new_membership_id == membership_id))
        .order_by(MembershipChange.created_at)
        .all()
    )


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
def post_membership(payload: MembershipCreate, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    membership = create_membership(db, payload.participant_id, payload.membership_type_id, payload.teacher_lesson_rate)
    log_action(db, operator, "membership_created", "membership", membership.id, f"Абонемент #{membership.id}", after=snapshot(membership, ["participant_id", "membership_type_id", "total_lessons", "remaining_lessons", "price", "teacher_lesson_rate", "status"]))
    return get_membership(membership.id, db)


@router.patch("/{membership_id}", response_model=MembershipRead)
def patch_membership(membership_id: int, payload: MembershipUpdate, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    existing = db.get(Membership, membership_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    before = snapshot(existing, ["total_lessons", "remaining_lessons", "price", "teacher_lesson_rate", "start_date", "end_date", "status"])
    membership = update_membership(db, membership_id, payload.model_dump(exclude_unset=True), operator.id)
    log_action(db, operator, "membership_updated", "membership", membership.id, f"Абонемент #{membership.id}", before=before, after=snapshot(membership, ["total_lessons", "remaining_lessons", "price", "teacher_lesson_rate", "start_date", "end_date", "status"]))
    return get_membership(membership.id, db)


@router.post("/{membership_id}/replace", response_model=MembershipRead)
def replace_membership_route(
    membership_id: int,
    payload: MembershipReplace,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_operator_access),
):
    membership = replace_membership(
        db,
        membership_id,
        payload.membership_type_id,
        payload.teacher_lesson_rate,
        payload.effective_date,
        payload.reason,
        operator.id,
    )
    log_action(
        db,
        operator,
        "membership_replaced",
        "membership",
        membership.id,
        f"Абонемент #{membership_id} → #{membership.id}",
        after={"old_membership_id": membership_id, "new_membership_id": membership.id, "membership_type_id": membership.membership_type_id},
    )
    return get_membership(membership.id, db)


@router.post("/{membership_id}/freeze", response_model=MembershipRead)
def freeze_membership(membership_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    membership = change_status(db, membership_id, MembershipStatus.FROZEN)
    log_action(db, operator, "membership_frozen", "membership", membership.id, f"Абонемент #{membership.id}", after=snapshot(membership, ["status"]))
    return get_membership(membership.id, db)


@router.post("/{membership_id}/unfreeze", response_model=MembershipRead)
def unfreeze_membership(membership_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    membership = unfreeze(db, membership_id)
    log_action(db, operator, "membership_unfrozen", "membership", membership.id, f"Абонемент #{membership.id}", after=snapshot(membership, ["status"]))
    return get_membership(membership.id, db)


@router.post("/{membership_id}/cancel", response_model=MembershipRead)
def cancel_membership(membership_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    existing = db.get(Membership, membership_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    if existing.status == MembershipStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Абонемент уже отменен")
    membership = change_status(db, membership_id, MembershipStatus.CANCELLED)
    log_action(db, operator, "membership_cancelled", "membership", membership.id, f"Абонемент #{membership.id}", after=snapshot(membership, ["status"]))
    return get_membership(membership.id, db)
