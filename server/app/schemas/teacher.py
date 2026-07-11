from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel


class TeacherBase(BaseModel):
    full_name: str
    phone: str | None = None
    comment: str | None = None
    teacher_share_percent: Decimal = Field(default=Decimal("50"), ge=0, le=100)
    is_active: bool = True


class TeacherCreate(TeacherBase):
    pass


class TeacherUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    comment: str | None = None
    teacher_share_percent: Decimal | None = Field(default=None, ge=0, le=100)
    is_active: bool | None = None


class TeacherRead(TeacherBase, ApiModel):
    id: int
    created_at: datetime
    updated_at: datetime
