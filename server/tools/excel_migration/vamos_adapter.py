"""Adapter for the inspected vamos-subscription-tracker SQLAlchemy models.

Never imports app.main, seeds demo data, guesses membership IDs, or commits
inside business services. VAMOS_IMPORT_DB must name an explicit destination.
"""
import json, os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Text, Integer, DateTime, create_engine, inspect, update
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker
from app.database import Base
from app.models import (Participant, Teacher, Membership, MembershipRevision, Payment, Visit,
                        ExtraExpense, ExpenseCategory, Operator, AuditLog, ScheduleEvent,
                        ScheduleEventParticipant, AttendanceStatus)
from app.services.financial_ledger import create_visit_entries
from vamos_importer import canonical_json, digest

class ExcelImportDelivery(Base):
    __tablename__='excel_import_deliveries'
    idempotency_key:Mapped[str]=mapped_column(String(64),primary_key=True)
    source_fingerprint:Mapped[str]=mapped_column(String(64))
    payload_hash:Mapped[str]=mapped_column(String(64))
    entity_type:Mapped[str]=mapped_column(String(40))
    entity_id:Mapped[int]=mapped_column(Integer)
    payload_json:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class VamosAdapter:
    def __init__(self, engine, operator_id, sites, channel_map):
        self.engine=engine;self.operator_id=int(operator_id);self.sites=sites;self.channel_map=channel_map
        self.factory=sessionmaker(bind=engine,autoflush=False);self.db=None

    @contextmanager
    def transaction(self):
        with self.factory() as db:
            self.db=db
            try:
                with db.begin():
                    if self.engine.dialect.name=='sqlite':db.connection().exec_driver_sql('BEGIN IMMEDIATE')
                    operator=db.get(Operator,self.operator_id)
                    if not operator or not operator.is_active or str(getattr(operator.role,'value',operator.role))!='admin':
                        raise ValueError('an active admin operator must own the import')
                    yield
            finally:self.db=None

    def assert_reference(self,kind,product_id):
        if kind=='site':
            if product_id not in self.sites:raise ValueError('unknown reviewed site')
            return
        classes={'student':Participant,'person':Participant,'teacher':Teacher,'session':ScheduleEvent,'category':ExpenseCategory}
        cls=classes[kind]
        value=self.db.get(cls,int(product_id))
        if not value:raise ValueError(f'missing {kind} reference')

    def deliver_once(self, idem, fingerprint, p):
        prior=self.db.get(ExcelImportDelivery,idem)
        payload_hash=digest(p)
        if prior:
            if prior.source_fingerprint!=fingerprint or prior.payload_hash!=payload_hash:raise ValueError('previous delivery has different source or payload')
            return False
        when=date.fromisoformat(p['date'])
        provenance=canonical_json({'migration':idem,'source':p['source'],'original_channel':p.get('channel'),'review':p['review_reason'],'site':p['site_id']})
        if p['kind']=='receipt':
            if p.get('category_id')!='membership_payment':raise ValueError('subscription receipt category must be membership_payment')
            if p.get('section')!='Абонементы':raise ValueError('only reviewed subscription receipts have a matching Payment model')
            m=self.db.get(Membership,int(p.get('membership_id') or 0))
            if not m or m.participant_id!=int(p.get('person_id') or 0):raise ValueError('receipt membership does not belong to participant')
            method=self.channel_map.get(p['channel'])
            if method not in ['cash','card']:raise ValueError('explicit cash/card channel mapping is required')
            amount=Decimal(p['amount'])
            if amount<=0 or amount>=Decimal('100000000'):raise ValueError('amount outside Numeric(10,2) range')
            row=Payment(participant_id=m.participant_id,membership_id=m.id,amount=amount,payment_date=when,payment_method=method,comment=provenance)
            self.db.add(row);entity='payment'
        elif p['kind']=='expense':
            if p.get('section','').casefold() in ['педагоги','преподаватели']:raise ValueError('teacher payouts require a separate cash ledger policy; not ExtraExpense')
            if not p.get('title') or len(p['title'])>255:raise ValueError('reviewed expense title required')
            amount=Decimal(p['amount'])
            if amount<=0 or amount>=Decimal('100000000'):raise ValueError('amount outside Numeric(10,2) range')
            row=ExtraExpense(title=p['title'],amount=amount,expense_date=when,comment=provenance,created_by_user_id=self.operator_id)
            self.db.add(row);entity='extra_expense'
        elif p['kind']=='attendance':
            m=self.db.get(Membership,int(p.get('membership_id') or 0))
            rev=self.db.get(MembershipRevision,int(p.get('revision_id') or 0))
            if not m or m.participant_id!=int(p['student_id']) or not rev or rev.membership_id!=m.id:raise ValueError('invalid membership/revision binding')
            if not (m.start_date<=when<=m.end_date) or rev.effective_from>when or (rev.effective_to and rev.effective_to<when):raise ValueError('historical terms do not cover visit date')
            event=self.db.get(ScheduleEvent,int(p['session_id']))
            if event.teacher_id!=int(p['teacher_id']) or event.starts_at.date()!=when or event.location!=self.sites[p['site_id']]:raise ValueError('schedule date/teacher/site mismatch')
            if str(getattr(event.status,'value',event.status))!='completed':raise ValueError('historical session must be confirmed completed')
            existing=self.db.query(ScheduleEventParticipant).filter_by(schedule_event_id=event.id,participant_id=m.participant_id).first()
            if existing and existing.visit_id:raise ValueError('session already has a visit; bind existing record instead of duplicating')
            if rev.lesson_count<=0:raise ValueError('invalid historical lesson count')
            lesson=Decimal(rev.lesson_price);earning=Decimal(rev.teacher_lesson_rate)
            if not (0<=earning<=lesson):raise ValueError('invalid historical financial split')
            mode=p.get('balance_mode')
            if mode=='decrement':
                updated=self.db.execute(update(Membership).where(Membership.id==m.id,Membership.remaining_lessons>0).values(remaining_lessons=Membership.remaining_lessons-1))
                if updated.rowcount!=1:raise ValueError('not enough remaining lessons')
            elif mode!='opening_balance_already_accounts_for_visit':raise ValueError('explicit opening balance policy is required')
            row=Visit(participant_id=m.participant_id,membership_id=m.id,membership_revision_id=rev.id,teacher_id=int(p['teacher_id']),visit_date=when,
                      lesson_price=lesson,teacher_lesson_rate=earning,teacher_earning=earning,school_earning=lesson-earning)
            self.db.add(row);self.db.flush()
            link=existing or ScheduleEventParticipant(schedule_event_id=event.id,participant_id=m.participant_id)
            link.visit_id=row.id;link.attendance_status=AttendanceStatus.ATTENDED;self.db.add(link)
            create_visit_entries(self.db,row,rev)
            entity='visit'
        else:raise ValueError('unsupported fact kind')
        self.db.flush()
        self.db.add(ExcelImportDelivery(idempotency_key=idem,source_fingerprint=fingerprint,payload_hash=payload_hash,entity_type=entity,entity_id=row.id,payload_json=canonical_json(p)))
        self.db.add(AuditLog(operator_id=self.operator_id,operator_name='Excel migration',action='excel_import',entity_type=entity,entity_id=row.id,
                             entity_label='Historical Excel import',after_json=canonical_json(p)))
        self.db.flush()
        return True

def create_adapter():
    url=os.environ.get('VAMOS_IMPORT_DB')
    if not url:raise ValueError('set VAMOS_IMPORT_DB explicitly; no default database is opened')
    config=json.loads(os.environ.get('VAMOS_IMPORT_CONFIG','{}'))
    if not config.get('operator_id') or not config.get('sites') or not config.get('channel_map'):raise ValueError('operator_id/sites/channel_map required in VAMOS_IMPORT_CONFIG')
    engine=create_engine(url)
    required={'participants','teachers','memberships','membership_revisions','payments','visits','financial_entries','operators','audit_logs','schedule_events','schedule_event_participants','extra_expenses','expense_categories'}
    if not required.issubset(set(inspect(engine).get_table_names())):
        engine.dispose()
        raise ValueError('destination lacks the verified Vamos schema; application tables are never created by this importer')
    # Explicit preparation is separate from business delivery; never initialize/seed application tables.
    ExcelImportDelivery.__table__.create(engine,checkfirst=True)
    return VamosAdapter(engine,config['operator_id'],config['sites'],config['channel_map'])
