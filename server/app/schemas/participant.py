from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ApiModel


class ParticipantBase(BaseModel):
    full_name: str
    phone: str | None = None
    comment: str | None = None
    is_active: bool = True


class ParticipantCreate(ParticipantBase):
    pass


class ParticipantUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    comment: str | None = None
    is_active: bool | None = None


class ParticipantRead(ParticipantBase, ApiModel):
    id: int
    created_at: datetime
    updated_at: datetime


class ParticipantListItem(ParticipantRead):
    active_membership_id: int | None = None
    active_membership_status: str | None = None
    remaining_lessons: int | None = None
    end_date: str | None = None
