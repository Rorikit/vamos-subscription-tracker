from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FinancialEntryType(str, PyEnum):
    LESSON_INCOME = "lesson_income"
    TEACHER_ACCRUAL = "teacher_accrual"
    LESSON_REVERSAL = "lesson_reversal"
    TEACHER_ACCRUAL_REVERSAL = "teacher_accrual_reversal"
    MEMBERSHIP_ADJUSTMENT = "membership_adjustment"
    MANUAL_CORRECTION = "manual_correction"


class FinancialDirection(str, PyEnum):
    INCOME = "income"
    EXPENSE = "expense"


class MembershipRevision(Base):
    __tablename__ = "membership_revisions"
    __table_args__ = (UniqueConstraint("membership_id", "revision_number", name="uq_membership_revision_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    membership_id: Mapped[int] = mapped_column(ForeignKey("memberships.id"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer)
    membership_type_id: Mapped[int] = mapped_column(ForeignKey("membership_types.id"))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    lesson_count: Mapped[int] = mapped_column(Integer)
    lesson_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    teacher_lesson_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_operator_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    membership = relationship("Membership", back_populates="revisions")
    membership_type = relationship("MembershipType")


class MembershipChange(Base):
    __tablename__ = "membership_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    old_membership_id: Mapped[int] = mapped_column(ForeignKey("memberships.id"), index=True)
    new_membership_id: Mapped[int] = mapped_column(ForeignKey("memberships.id"), index=True)
    effective_at: Mapped[date] = mapped_column(Date)
    transfer_mode: Mapped[str] = mapped_column(String(24), default="lessons")
    transferred_lessons: Mapped[int] = mapped_column(Integer, default=0)
    transferred_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    reason: Mapped[str] = mapped_column(Text)
    created_by_operator_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FinancialEntry(Base):
    __tablename__ = "financial_entries"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "entry_type", name="uq_financial_entry_source_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"), nullable=True, index=True)
    membership_id: Mapped[int | None] = mapped_column(ForeignKey("memberships.id"), nullable=True, index=True)
    membership_revision_id: Mapped[int | None] = mapped_column(ForeignKey("membership_revisions.id"), nullable=True, index=True)
    visit_id: Mapped[int | None] = mapped_column(ForeignKey("visits.id"), nullable=True, index=True)
    entry_type: Mapped[FinancialEntryType] = mapped_column(SqlEnum(FinancialEntryType))
    direction: Mapped[FinancialDirection] = mapped_column(SqlEnum(FinancialDirection))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    effective_date: Mapped[date] = mapped_column(Date, index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[int] = mapped_column(Integer)
    reverses_entry_id: Mapped[int | None] = mapped_column(ForeignKey("financial_entries.id"), nullable=True, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_operator_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    revision = relationship("MembershipRevision")
    reversed_entry = relationship("FinancialEntry", remote_side=[id], uselist=False)
