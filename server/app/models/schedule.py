from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScheduleEventStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ScheduleEventType(str, Enum):
    GROUP = "group"
    INDIVIDUAL = "individual"
    OTHER = "other"


class AttendanceStatus(str, Enum):
    PLANNED = "planned"
    ATTENDED = "attended"
    ABSENT = "absent"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class ScheduleEvent(Base):
    __tablename__ = "schedule_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[ScheduleEventStatus] = mapped_column(String(20), default=ScheduleEventStatus.SCHEDULED, index=True)
    event_type: Mapped[ScheduleEventType] = mapped_column(String(20), default=ScheduleEventType.GROUP)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    recurrence_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    recurrence_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    teacher = relationship("Teacher", back_populates="schedule_events")
    participants = relationship("ScheduleEventParticipant", back_populates="schedule_event", cascade="all, delete-orphan")


class ScheduleEventParticipant(Base):
    __tablename__ = "schedule_event_participants"
    __table_args__ = (
        UniqueConstraint("schedule_event_id", "participant_id", name="uq_schedule_event_participant"),
        UniqueConstraint("visit_id", name="uq_schedule_event_participant_visit"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    schedule_event_id: Mapped[int] = mapped_column(ForeignKey("schedule_events.id"), index=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    attendance_status: Mapped[AttendanceStatus] = mapped_column(String(20), default=AttendanceStatus.PLANNED)
    visit_id: Mapped[int | None] = mapped_column(ForeignKey("visits.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    schedule_event = relationship("ScheduleEvent", back_populates="participants")
    participant = relationship("Participant", back_populates="schedule_events")
    visit = relationship("Visit", back_populates="schedule_participant")
