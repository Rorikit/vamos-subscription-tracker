from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Membership, Payment, Visit
from app.schemas.finance import FinanceSummary, TeacherEarning
from app.schemas.payment import PaymentRead
from app.schemas.visit import VisitRead
from app.services.auth import require_finance_access
from app.services.finance import get_summary, get_teacher_earnings

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/summary", response_model=FinanceSummary)
def summary(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    teacher_id: int | None = Query(default=None),
    membership_type_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _operator=Depends(require_finance_access),
):
    return get_summary(db, date_from=date_from, date_to=date_to, teacher_id=teacher_id, membership_type_id=membership_type_id, payment_method=payment_method)


@router.get("/teacher-earnings", response_model=list[TeacherEarning])
def teacher_earnings(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    teacher_id: int | None = Query(default=None),
    membership_type_id: int | None = Query(default=None),
    include_cancelled: bool = Query(default=False),
    db: Session = Depends(get_db),
    _operator=Depends(require_finance_access),
):
    return get_teacher_earnings(db, date_from=date_from, date_to=date_to, teacher_id=teacher_id, membership_type_id=membership_type_id, include_cancelled=include_cancelled)


@router.get("/payments", response_model=list[PaymentRead])
def payments(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    membership_type_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _operator=Depends(require_finance_access),
):
    query = db.query(Payment).options(joinedload(Payment.participant))
    if date_from:
        query = query.filter(Payment.payment_date >= date_from)
    if date_to:
        query = query.filter(Payment.payment_date <= date_to)
    if membership_type_id:
        query = query.join(Membership, Payment.membership_id == Membership.id).filter(Membership.membership_type_id == membership_type_id)
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)
    return query.order_by(Payment.payment_date.desc(), Payment.id.desc()).limit(200).all()


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    from app.services.memberships import serialize_membership

    memberships = (
        db.query(Membership)
        .options(joinedload(Membership.participant), joinedload(Membership.membership_type))
        .order_by(Membership.end_date)
        .all()
    )
    recent_payments = (
        db.query(Payment)
        .options(joinedload(Payment.participant))
        .order_by(Payment.payment_date.desc(), Payment.id.desc())
        .limit(8)
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
        "payments": recent_payments,
        "visits": recent_visits,
    }
