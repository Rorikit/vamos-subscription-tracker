from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Operator
from app.models.water import WaterReceipt
from app.schemas.water import WaterReceiptCreate, WaterReceiptRead, WaterSummary
from app.services.auth import get_current_operator, require_operator_access, require_admin
from app.services.audit import log_action, snapshot
from app.services.water import water_query, water_summary, create_water, cancel_water, serialize_water

router = APIRouter(tags=["water"])

@router.get("/water-receipts/summary", response_model=WaterSummary)
def summary(date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), operator: Operator = Depends(get_current_operator)):
    return water_summary(db, date_from, date_to)

@router.get("/water-receipts", response_model=list[WaterReceiptRead])
def receipts(date_from: date | None = None, date_to: date | None = None, search: str | None = None,
             status: Literal["active", "cancelled"] | None = None, page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=200),
             db: Session = Depends(get_db), operator: Operator = Depends(get_current_operator)):
    rows = water_query(db, date_from, date_to, status).options(joinedload(WaterReceipt.created_by)).order_by(WaterReceipt.received_on.desc(), WaterReceipt.id.desc()).all()
    if search:
        needle = search.strip().casefold()
        rows = [r for r in rows if needle in "вода" or needle in (r.comment or "").casefold()]
    return [serialize_water(r) for r in rows[(page - 1)*page_size:page*page_size]]

@router.post("/water-receipts", response_model=WaterReceiptRead)
def create(payload: WaterReceiptCreate, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    row, created = create_water(db, payload, operator)
    if created: log_action(db, operator, "water_receipt_created", "water_receipt", row.id, "Вода", after=snapshot(row, ["amount", "received_on", "payment_method", "comment"]))
    return serialize_water(row)

@router.post("/water-receipts/{receipt_id}/cancel", response_model=WaterReceiptRead)
def cancel(receipt_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    row = cancel_water(db, receipt_id, operator)
    log_action(db, operator, "water_receipt_cancelled", "water_receipt", row.id, "Вода", after=snapshot(row, ["status", "cancelled_at"]))
    return serialize_water(row)

@router.delete("/water-receipts/{receipt_id}", status_code=204)
def delete(receipt_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    from fastapi import HTTPException
    row = db.get(WaterReceipt, receipt_id)
    if not row: raise HTTPException(404, "Поступление за воду не найдено")
    before = snapshot(row, ["amount", "received_on", "payment_method", "status"])
    db.delete(row); db.commit()
    log_action(db, operator, "water_receipt_deleted", "water_receipt", receipt_id, "Вода", before=before)
