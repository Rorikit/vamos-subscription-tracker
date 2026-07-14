from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Membership, Operator, Participant, Payment
from app.schemas.payment import PaymentCreate, PaymentRead
from app.services.audit import log_action, snapshot
from app.services.auth import require_admin, require_operator_access

router = APIRouter(tags=["payments"])


@router.get("/participants/{participant_id}/payments", response_model=list[PaymentRead])
def list_participant_payments(participant_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Payment)
        .options(joinedload(Payment.participant))
        .filter(Payment.participant_id == participant_id)
        .order_by(Payment.payment_date.desc(), Payment.id.desc())
        .all()
    )


@router.post("/payments", response_model=PaymentRead)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    if not db.get(Participant, payload.participant_id):
        raise HTTPException(status_code=404, detail="Участник не найден")
    membership = db.get(Membership, payload.membership_id)
    if not membership or membership.participant_id != payload.participant_id:
        raise HTTPException(status_code=404, detail="Абонемент участника не найден")

    payment = Payment(**payload.model_dump(exclude={"payment_date"}), payment_date=payload.payment_date or date.today())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    log_action(db, operator, "payment_created", "payment", payment.id, f"Оплата #{payment.id}", after=snapshot(payment, ["participant_id", "membership_id", "amount", "payment_method", "is_cancelled"]))
    return payment


@router.post("/payments/{payment_id}/cancel", response_model=PaymentRead)
def cancel_payment(payment_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Оплата не найдена")
    payment.is_cancelled = True
    db.add(payment)
    db.commit()
    db.refresh(payment)
    log_action(db, operator, "payment_cancelled", "payment", payment.id, f"Оплата #{payment.id}", before={"is_cancelled": False}, after=snapshot(payment, ["is_cancelled"]))
    return payment
