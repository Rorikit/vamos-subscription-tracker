from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Membership, Operator, Visit
from app.schemas.visit import VisitRead
from app.services.audit import log_action, snapshot
from app.services.auth import require_admin
from app.services.memberships import cancel_visit

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


@router.post("/visits/{visit_id}/cancel", response_model=VisitRead)
def cancel(visit_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    visit = cancel_visit(db, visit_id)
    log_action(db, operator, "visit_returned", "visit", visit.id, f"Занятие #{visit.id}", before={"is_cancelled": False}, after=snapshot(visit, ["is_cancelled"]))
    return visit
