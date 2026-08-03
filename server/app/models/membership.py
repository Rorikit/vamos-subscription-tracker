from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MembershipStatus(str, PyEnum):
    ACTIVE = "active"
    FINISHED = "finished"
    EXPIRED = "expired"
    FROZEN = "frozen"
    CANCELLED = "cancelled"


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    membership_type_id: Mapped[int] = mapped_column(ForeignKey("membership_types.id"))
    total_lessons: Mapped[int] = mapped_column(Integer)
    remaining_lessons: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    teacher_lesson_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[MembershipStatus] = mapped_column(SqlEnum(MembershipStatus), default=MembershipStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    participant = relationship("Participant", back_populates="memberships")
    membership_type = relationship("MembershipType", back_populates="memberships")
    visits = relationship("Visit", back_populates="membership")
    payments = relationship("Payment", back_populates="membership")
