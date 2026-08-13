from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PracticeRentalStatus(str, PyEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class PracticeTariff(Base):
    __tablename__ = "practice_tariffs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rentals = relationship("PracticeRental", back_populates="tariff")


class PracticeRental(Base):
    __tablename__ = "practice_rentals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    registered_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), index=True)
    tariff_id: Mapped[int | None] = mapped_column(ForeignKey("practice_tariffs.id"), nullable=True, index=True)
    tariff_name_snapshot: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    practiced_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[PracticeRentalStatus] = mapped_column(SqlEnum(PracticeRentalStatus), default=PracticeRentalStatus.ACTIVE, index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    registered_teacher = relationship("Teacher")
    tariff = relationship("PracticeTariff", back_populates="rentals")
    created_by = relationship("Operator", foreign_keys=[created_by_user_id])
    cancelled_by = relationship("Operator", foreign_keys=[cancelled_by_user_id])
