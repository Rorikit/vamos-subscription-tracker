import unittest
from datetime import date,datetime
from decimal import Decimal
from sqlalchemy import create_engine,select,event
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Participant,Teacher,MembershipType,Membership,MembershipRevision,Operator,Payment,Visit,FinancialEntry,ScheduleEvent,ExpenseCategory,ExtraExpense,AuditLog
from vamos_adapter import VamosAdapter,ExcelImportDelivery
from apply_reviewed import deliver

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite:///:memory:')
        @event.listens_for(self.engine,'connect')
        def fk(dbapi,record):dbapi.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db,db.begin():
            db.add_all([Operator(id=1,username='migration-admin',full_name='Import operator',role='admin',password_hash='test-only'),Participant(id=1,full_name='Example A.'),Teacher(id=1,full_name='Example Teacher'),ExpenseCategory(id=1,name='Other'),MembershipType(id=1,name='Legacy 8',lesson_count=8,price=Decimal('6200'),validity_days=90)])
            db.flush()
            db.add(Membership(id=1,participant_id=1,membership_type_id=1,total_lessons=8,remaining_lessons=3,price=Decimal('6200'),teacher_lesson_rate=Decimal('300'),start_date=date(2026,9,1),end_date=date(2026,12,1)))
            db.flush()
            db.add(MembershipRevision(id=1,membership_id=1,revision_number=1,membership_type_id=1,price=Decimal('6200'),lesson_count=8,lesson_price=Decimal('775'),teacher_lesson_rate=Decimal('300'),effective_from=date(2026,9,1)))
            db.add(ScheduleEvent(id=1,title='Legacy group',teacher_id=1,starts_at=datetime(2026,10,7,19),ends_at=datetime(2026,10,7,20),status='completed',location='Hall'))
        self.adapter=VamosAdapter(self.engine,1,{'hall':'Hall'},{'cash':'cash','bank':'card','qr':'card','yookassa':'card'})
        self.receipt={'idempotency_key':'receipt-key','source_fingerprint':'batch','source':{'source_key':'income','sheet_index':1,'row':3},'date':'2026-10-07','site_id':'hall','kind':'receipt','person_id':'1','membership_id':'1','amount':'1200.00','channel':'qr','cell':'E3','category_id':'membership_payment','section':'Абонементы','review_reason':'Verified receipt'}
    def tearDown(self):self.engine.dispose()
    def count(self,cls):
        with Session(self.engine) as db:return len(db.scalars(select(cls)).all())
    def test_receipt_repeat_and_channel(self):
        self.assertEqual(deliver([self.receipt],self.adapter),1);self.assertEqual(deliver([self.receipt],self.adapter),0)
        self.assertEqual(self.count(Payment),1);self.assertEqual(self.count(ExcelImportDelivery),1);self.assertEqual(self.count(AuditLog),1)
        with Session(self.engine) as db:self.assertEqual(db.get(Payment,1).payment_method,'card')
    def test_all_or_nothing(self):
        bad={**self.receipt,'idempotency_key':'bad','membership_id':'999'}
        with self.assertRaises(ValueError):deliver([self.receipt,bad],self.adapter)
        self.assertEqual(self.count(Payment),0);self.assertEqual(self.count(ExcelImportDelivery),0)
    def test_changed_payload_not_silent_overwrite(self):
        deliver([self.receipt],self.adapter)
        with self.assertRaises(ValueError):deliver([{**self.receipt,'amount':'2000'}],self.adapter)
        self.assertEqual(self.count(Payment),1)
    def test_unmapped_channel_blocked(self):
        with self.assertRaises(ValueError):deliver([{**self.receipt,'channel':'unmapped'}],self.adapter)
        self.assertEqual(self.count(Payment),0)
    def test_non_subscription_receipt_not_reclassified(self):
        with self.assertRaises(ValueError):deliver([{**self.receipt,'section':'Бар'}],self.adapter)
    def test_visit_and_ledger_with_opening_balance(self):
        p={**self.receipt,'idempotency_key':'attendance-key','kind':'attendance','student_id':'1','teacher_id':'1','session_id':'1','revision_id':'1','balance_mode':'opening_balance_already_accounts_for_visit'}
        self.assertEqual(deliver([p],self.adapter),1);self.assertEqual(deliver([p],self.adapter),0)
        self.assertEqual(self.count(Visit),1);self.assertEqual(self.count(FinancialEntry),2)
        with Session(self.engine) as db:self.assertEqual(db.get(Membership,1).remaining_lessons,3)
    def test_visit_decrement_once(self):
        p={**self.receipt,'idempotency_key':'visit-decrement','kind':'attendance','student_id':'1','teacher_id':'1','session_id':'1','revision_id':'1','balance_mode':'decrement'}
        deliver([p],self.adapter);deliver([p],self.adapter)
        with Session(self.engine) as db:self.assertEqual(db.get(Membership,1).remaining_lessons,2)
    def test_teacher_payout_not_extra_expense(self):
        p={**self.receipt,'kind':'expense','category_id':'1','title':'Salary','section':'Преподаватели'}
        with self.assertRaises(ValueError):deliver([p],self.adapter)
        self.assertEqual(self.count(ExtraExpense),0)

if __name__=='__main__':unittest.main()
