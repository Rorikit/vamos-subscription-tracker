from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.schedule import AttendanceStatus, ScheduleEventStatus, ScheduleEventType
from app.schemas.common import ApiModel, ParticipantSnapshot, TeacherSnapshot
from app.schemas.visit import VisitRead


class ScheduleParticipantInput(BaseModel):
    participant_id: int
    attendance_status: AttendanceStatus = AttendanceStatus.PLANNED


class ScheduleEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    teacher_id: int
    starts_at: datetime
    ends_at: datetime
    event_type: ScheduleEventType = ScheduleEventType.GROUP
    location: str | None = None
    color: str | None = None
    participant_ids: list[int] = Field(default_factory=list)
    recurrence: dict | None = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        if len(value) not in {4, 7} or not value.startswith("#"):
            raise ValueError("Цвет должен быть в формате HEX")
        return value


class ScheduleEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    teacher_id: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    event_type: ScheduleEventType | None = None
    location: str | None = None
    color: str | None = None
    participant_ids: list[int] | None = None
    scope: str = "single"


class ScheduleEventMove(BaseModel):
    starts_at: datetime
    ends_at: datetime
    scope: str = "single"


class ScheduleEventComplete(BaseModel):
    participants: list[ScheduleParticipantInput]


class ScheduleEventParticipantAdd(BaseModel):
    participant_id: int


class ScheduleConflictRead(ApiModel):
    event_id: int
    title: str
    teacher_name: str | None = None
    starts_at: datetime
    ends_at: datetime


class ScheduleEventParticipantRead(ApiModel):
    id: int
    schedule_event_id: int
    participant_id: int
    attendance_status: AttendanceStatus
    visit_id: int | None = None
    participant: ParticipantSnapshot | None = None
    visit: VisitRead | None = None
    created_at: datetime
    updated_at: datetime


class ScheduleEventRead(ApiModel):
    id: int
    title: str
    description: str | None = None
    teacher_id: int
    starts_at: datetime
    ends_at: datetime
    status: ScheduleEventStatus
    event_type: ScheduleEventType
    location: str | None = None
    color: str | None = None
    recurrence_group_id: str | None = None
    recurrence_rule: str | None = None
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    teacher: TeacherSnapshot | None = None
    participants: list[ScheduleEventParticipantRead] = []
    created_at: datetime
    updated_at: datetime
