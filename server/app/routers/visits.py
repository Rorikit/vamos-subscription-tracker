from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Membership, Operator, Visit
from app.schemas.visit import VisitRead, VisitWriteOff
from app.services.audit import log_action, snapshot
from app.services.auth import require_admin, require_operator_access
from app.services.memberships import cancel_visit, write_off_visit

router = APIRouter(tags=["visits"])


@router.get("/participants/{participant_id}/visits", response_model=list[VisitRead])
def list_participant_visits(participant_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Visit)
        .options(
            joinedload(Visit.participant),
            joinedload(Visit.teacher),
            joinedload(Visit.membership).joinedload(Membership.membership_type),
        )
        .filter(Visit.participant_id == participant_id)
        .order_by(Visit.visit_date.desc(), Visit.id.desc())
        .all()
    )


@router.post("/visits/write-off", response_model=VisitRead)
def write_off(payload: VisitWriteOff, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    visit = write_off_visit(db, payload.participant_id, payload.membership_id, payload.teacher_id, payload.visit_date)
    log_action(db, operator, "visit_written_off", "visit", visit.id, f"Занятие #{visit.id}", after=snapshot(visit, ["participant_id", "membership_id", "teacher_id", "visit_date", "lesson_price"]))
    return visit


@router.post("/visits/{visit_id}/cancel", response_model=VisitRead)
def cancel(visit_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    visit = cancel_visit(db, visit_id)
    log_action(db, operator, "visit_returned", "visit", visit.id, f"Занятие #{visit.id}", before={"is_cancelled": False}, after=snapshot(visit, ["is_cancelled"]))
    return visit
