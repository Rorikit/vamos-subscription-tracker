from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    membership_id: Mapped[int] = mapped_column(ForeignKey("memberships.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), index=True)
    visit_date: Mapped[date] = mapped_column(Date)
    lesson_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    teacher_share_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    teacher_earning: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    school_earning: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    participant = relationship("Participant", back_populates="visits")
    membership = relationship("Membership", back_populates="visits")
    teacher = relationship("Teacher", back_populates="visits")

    @property
    def membership_type(self):
        return self.membership.membership_type if self.membership else None
