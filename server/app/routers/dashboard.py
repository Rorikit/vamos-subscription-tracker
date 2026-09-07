from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Membership, Visit
from app.services.finance import get_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db)):
    from app.services.memberships import serialize_membership

    memberships = (
        db.query(Membership)
        .options(joinedload(Membership.participant), joinedload(Membership.membership_type))
        .order_by(Membership.end_date)
        .all()
    )
    recent_visits = (
        db.query(Visit)
        .options(
            joinedload(Visit.participant),
            joinedload(Visit.teacher),
            joinedload(Visit.membership).joinedload(Membership.membership_type),
        )
        .order_by(Visit.visit_date.desc(), Visit.id.desc())
        .limit(8)
        .all()
    )
    return {
        "summary": get_summary(db),
        "memberships": [serialize_membership(db, membership) for membership in memberships],
        "visits": recent_visits,
    }
