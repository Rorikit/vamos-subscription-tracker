from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    membership_id: Mapped[int] = mapped_column(ForeignKey("memberships.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payment_date: Mapped[date] = mapped_column(Date)
    payment_method: Mapped[str] = mapped_column(String(80), default="cash")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    participant = relationship("Participant", back_populates="payments")
    membership = relationship("Membership", back_populates="payments")

