from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExtraExpenseStatus(str, PyEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class ExtraExpense(Base):
    __tablename__ = "extra_expenses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    expense_date: Mapped[date] = mapped_column(Date, index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ExtraExpenseStatus] = mapped_column(SqlEnum(ExtraExpenseStatus), default=ExtraExpenseStatus.ACTIVE, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = relationship("Operator", foreign_keys=[created_by_user_id])
    cancelled_by = relationship("Operator", foreign_keys=[cancelled_by_user_id])
