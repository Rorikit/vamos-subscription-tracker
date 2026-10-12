from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from app.models.water import WaterReceipt
from app.services.lesson_finance import quantize_money

def water_query(db, date_from=None, date_to=None, status="active"):
    query = db.query(WaterReceipt)
    if status: query = query.filter(WaterReceipt.status == status)
    if date_from: query = query.filter(WaterReceipt.received_on >= date_from)
    if date_to: query = query.filter(WaterReceipt.received_on <= date_to)
    return query

def serialize_water(row):
    return {"id": row.id, "amount": row.amount, "received_on": row.received_on,
            "payment_method": row.payment_method, "status": row.status, "comment": row.comment,
            "created_by_user_id": row.created_by_user_id,
            "created_by_name": row.created_by.full_name if row.created_by else None,
            "cancelled_at": row.cancelled_at, "created_at": row.created_at}

def create_water(db, payload, operator):
    def existing():
        row = db.query(WaterReceipt).filter_by(request_id=str(payload.request_id)).first()
        if row:
            if (row.amount, row.received_on, row.payment_method, row.comment, row.created_by_user_id) != (payload.amount, payload.received_on, payload.payment_method, payload.comment, operator.id):
                raise HTTPException(409, "Этот запрос уже использован для другого поступления")
        return row
    row = existing()
    if row: return row, False
    row = WaterReceipt(amount=payload.amount, received_on=payload.received_on, payment_method=payload.payment_method,
                       comment=payload.comment, request_id=str(payload.request_id), created_by_user_id=operator.id)
    db.add(row)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        row = existing()
        if not row: raise
        return row, False
    db.refresh(row)
    return row, True

def cancel_water(db, receipt_id, operator):
    row = db.get(WaterReceipt, receipt_id)
    if not row: raise HTTPException(404, "Поступление за воду не найдено")
    if row.status == "cancelled": raise HTTPException(409, "Поступление уже отменено")
    row.status = "cancelled"; row.cancelled_at = datetime.utcnow(); row.cancelled_by_user_id = operator.id
    db.commit(); db.refresh(row)
    return row

def water_summary(db, date_from=None, date_to=None):
    rows = water_query(db, date_from, date_to).all()
    return {"income_total": quantize_money(sum((r.amount for r in rows), Decimal(0))), "receipts_count": len(rows)}
