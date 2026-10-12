from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class WaterReceipt(Base):
    __tablename__ = "water_receipts"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_water_amount_positive"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    received_on: Mapped[date] = mapped_column(Date, index=True)
    payment_method: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("operators.id"))
    cancelled_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by = relationship("Operator", foreign_keys=[created_by_user_id])
