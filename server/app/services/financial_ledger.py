from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    FinancialDirection,
    FinancialEntry,
    FinancialEntryType,
    Membership,
    MembershipRevision,
    Visit,
)
from app.services.lesson_finance import quantize_money


def current_membership_revision(db: Session, membership: Membership, effective_date: date | None = None) -> MembershipRevision:
    if membership.total_lessons <= 0:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="В абонементе некорректное количество занятий")
    target_date = effective_date or date.today()
    revision = (
        db.query(MembershipRevision)
        .filter(
            MembershipRevision.membership_id == membership.id,
            MembershipRevision.effective_from <= target_date,
            (MembershipRevision.effective_to.is_(None)) | (MembershipRevision.effective_to >= target_date),
        )
        .order_by(MembershipRevision.revision_number.desc())
        .first()
    )
    if revision:
        terms_changed = (
            revision.membership_type_id != membership.membership_type_id
            or revision.lesson_count != membership.total_lessons
            or quantize_money(Decimal(revision.price)) != quantize_money(Decimal(membership.price))
            or quantize_money(Decimal(revision.teacher_lesson_rate)) != quantize_money(Decimal(membership.teacher_lesson_rate or 0))
        )
        if not terms_changed:
            return revision
        return create_membership_revision(db, membership, target_date, "Изменение условий абонемента")
    return create_membership_revision(db, membership, effective_from=membership.start_date, reason="Миграция исходных условий")


def create_membership_revision(
    db: Session,
    membership: Membership,
    effective_from: date,
    reason: str,
    operator_id: int | None = None,
) -> MembershipRevision:
    previous = (
        db.query(MembershipRevision)
        .filter(MembershipRevision.membership_id == membership.id)
        .order_by(MembershipRevision.revision_number.desc())
        .first()
    )
    if previous and previous.effective_to is None:
        previous.effective_to = effective_from
        db.add(previous)
    lesson_price = quantize_money(Decimal(membership.price) / Decimal(membership.total_lessons))
    revision = MembershipRevision(
        membership_id=membership.id,
        revision_number=(previous.revision_number + 1) if previous else 1,
        membership_type_id=membership.membership_type_id,
        price=quantize_money(Decimal(membership.price)),
        lesson_count=membership.total_lessons,
        lesson_price=lesson_price,
        teacher_lesson_rate=quantize_money(Decimal(membership.teacher_lesson_rate or 0)),
        effective_from=effective_from,
        change_reason=reason,
        created_by_operator_id=operator_id,
    )
    db.add(revision)
    db.flush()
    return revision


def create_visit_entries(db: Session, visit: Visit, revision: MembershipRevision) -> None:
    existing = db.query(FinancialEntry.id).filter(FinancialEntry.source_type == "visit", FinancialEntry.source_id == visit.id).first()
    if existing:
        return
    db.add_all(
        [
            FinancialEntry(
                participant_id=visit.participant_id,
                membership_id=visit.membership_id,
                membership_revision_id=revision.id,
                visit_id=visit.id,
                entry_type=FinancialEntryType.LESSON_INCOME,
                direction=FinancialDirection.INCOME,
                amount=quantize_money(Decimal(visit.lesson_price or 0)),
                effective_date=visit.visit_date,
                source_type="visit",
                source_id=visit.id,
                description=f"Доход по занятию #{visit.id}",
            ),
            FinancialEntry(
                participant_id=visit.participant_id,
                membership_id=visit.membership_id,
                membership_revision_id=revision.id,
                visit_id=visit.id,
                entry_type=FinancialEntryType.TEACHER_ACCRUAL,
                direction=FinancialDirection.EXPENSE,
                amount=quantize_money(Decimal(visit.teacher_earning or 0)),
                effective_date=visit.visit_date,
                source_type="visit",
                source_id=visit.id,
                description=f"Начисление преподавателю по занятию #{visit.id}",
            ),
        ]
    )
    db.flush()


def reverse_visit_entries(db: Session, visit: Visit) -> None:
    originals = (
        db.query(FinancialEntry)
        .filter(
            FinancialEntry.source_type == "visit",
            FinancialEntry.source_id == visit.id,
            FinancialEntry.entry_type.in_([FinancialEntryType.LESSON_INCOME, FinancialEntryType.TEACHER_ACCRUAL]),
        )
        .all()
    )
    for original in originals:
        if db.query(FinancialEntry.id).filter(FinancialEntry.reverses_entry_id == original.id).first():
            continue
        is_income = original.entry_type == FinancialEntryType.LESSON_INCOME
        db.add(
            FinancialEntry(
                participant_id=original.participant_id,
                membership_id=original.membership_id,
                membership_revision_id=original.membership_revision_id,
                visit_id=visit.id,
                entry_type=FinancialEntryType.LESSON_REVERSAL if is_income else FinancialEntryType.TEACHER_ACCRUAL_REVERSAL,
                direction=FinancialDirection.EXPENSE if is_income else FinancialDirection.INCOME,
                amount=original.amount,
                effective_date=date.today(),
                source_type="visit_reversal",
                source_id=visit.id,
                reverses_entry_id=original.id,
                description=f"Возврат финансовой операции #{original.id}",
            )
        )
    db.flush()


def backfill_financial_ledger(db: Session) -> tuple[int, int]:
    revisions_created = 0
    entries_created = 0
    for membership in db.query(Membership).order_by(Membership.id).all():
        before = db.query(MembershipRevision).filter(MembershipRevision.membership_id == membership.id).count()
        current_membership_revision(db, membership, membership.start_date)
        if before == 0:
            revisions_created += 1

    for visit in db.query(Visit).order_by(Visit.id).all():
        membership = db.get(Membership, visit.membership_id)
        if not membership:
            continue
        revision = current_membership_revision(db, membership, visit.visit_date)
        visit.membership_revision_id = revision.id
        before = db.query(FinancialEntry).filter(FinancialEntry.source_type == "visit", FinancialEntry.source_id == visit.id).count()
        create_visit_entries(db, visit, revision)
        if before == 0:
            entries_created += 2
        if visit.is_cancelled:
            reverse_visit_entries(db, visit)
        db.add(visit)
    db.commit()
    return revisions_created, entries_created
