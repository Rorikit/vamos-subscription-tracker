from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ParticipantSnapshot(ApiModel):
    id: int
    full_name: str
    phone: str | None = None


class MembershipTypeSnapshot(ApiModel):
    id: int
    name: str


class TeacherSnapshot(ApiModel):
    id: int
    full_name: str


class TimestampFields(ApiModel):
    created_at: datetime
    updated_at: datetime


class DateRange(ApiModel):
    start_date: date
    end_date: date
