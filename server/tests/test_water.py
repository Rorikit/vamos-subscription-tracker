from datetime import date
from decimal import Decimal
from uuid import uuid4
import unittest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Operator, OperatorRole, Participant, Membership, Visit, PracticeRental
from app.models.water import WaterReceipt
from app.schemas.water import WaterReceiptCreate, WaterReceiptRead
from app.services.water import create_water, cancel_water, water_summary, water_query, serialize_water
from app.services.finance import get_summary, get_monthly_report
from app.services.auth import require_operator_access, require_admin
from app.routers.water import create as create_endpoint

class WaterTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.op = Operator(username="test", full_name="Test", role=OperatorRole.ADMIN, password_hash="unused")
        self.db.add(self.op); self.db.commit()
    def tearDown(self): self.db.close(); self.engine.dispose()
    def payload(self, **kw):
        return WaterReceiptCreate(**{"amount":"150.50", "received_on":"2026-10-12", "payment_method":"cash", "request_id":str(uuid4()), **kw})
    def test_create_without_person_or_tariff(self):
        row, fresh = create_water(self.db, self.payload(), self.op)
        self.assertTrue(fresh); self.assertEqual(row.amount, Decimal("150.50"))
        self.assertEqual(WaterReceiptRead.model_validate(serialize_water(row)).created_by_name, "Test")
        for cls in [Participant, Membership, Visit, PracticeRental]: self.assertEqual(self.db.query(cls).count(), 0)
    def test_cash_card_and_monthly_report(self):
        create_water(self.db, self.payload(), self.op)
        create_water(self.db, self.payload(amount="200", payment_method="card"), self.op)
        summary=get_summary(self.db, date_from=date(2026,10,1), date_to=date(2026,10,31))
        self.assertEqual(summary["water_income"], Decimal("350.50"))
        self.assertEqual(summary["income_total"], Decimal("350.50"))
        self.assertEqual(summary["cash_income"], Decimal("150.50")); self.assertEqual(summary["card_income"], Decimal("200.00"))
        self.assertEqual(summary["practice_income"], 0); self.assertEqual(summary["teacher_earnings_total"], 0)
        report=get_monthly_report(self.db,2026,10);self.assertEqual(report["water_income"],Decimal("350.50"))
    def test_cancel_removes_from_income_preserves_history(self):
        row,_=create_water(self.db,self.payload(),self.op);cancel_water(self.db,row.id,self.op)
        self.assertEqual(water_summary(self.db)["income_total"],0);self.assertEqual(get_summary(self.db)["water_income"],0)
        self.assertEqual(water_query(self.db,status=None).count(),1)
        with self.assertRaises(HTTPException):cancel_water(self.db,row.id,self.op)
    def test_date_boundaries(self):
        create_water(self.db,self.payload(received_on="2026-09-30"),self.op)
        create_water(self.db,self.payload(received_on="2026-10-01"),self.op)
        create_water(self.db,self.payload(received_on="2026-10-31"),self.op)
        create_water(self.db,self.payload(received_on="2026-11-01"),self.op)
        self.assertEqual(water_summary(self.db,date(2026,10,1),date(2026,10,31))["receipts_count"],2)
    def test_retry_does_not_duplicate(self):
        payload=self.payload();first,fresh=create_water(self.db,payload,self.op);second,fresh=create_water(self.db,payload,self.op)
        self.assertFalse(fresh);self.assertEqual(first.id,second.id);self.assertEqual(self.db.query(WaterReceipt).count(),1)
        with self.assertRaises(HTTPException):create_water(self.db,self.payload(request_id=payload.request_id,amount="200"),self.op)
    def test_invalid_amount_and_method(self):
        for value in ["0","-1","150.001","NaN","100000000"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):self.payload(amount=value)
        with self.assertRaises(ValidationError):self.payload(payment_method="other")
    def test_finance_read_only_and_operator_no_delete(self):
        finance=Operator(role=OperatorRole.FINANCE)
        with self.assertRaises(HTTPException):require_operator_access(finance)
        with self.assertRaises(HTTPException):require_admin(Operator(role=OperatorRole.OPERATOR))
    def test_endpoint_audit_once(self):
        from app.models import AuditLog
        payload=self.payload();create_endpoint(payload,self.db,self.op);create_endpoint(payload,self.db,self.op)
        self.assertEqual(self.db.query(AuditLog).count(),1)

if __name__=="__main__":unittest.main()
