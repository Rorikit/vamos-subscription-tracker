from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ApiModel


class TeacherBase(BaseModel):
    full_name: str
    phone: str | None = None
    comment: str | None = None
    is_active: bool = True


class TeacherCreate(TeacherBase):
    pass


class TeacherUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    comment: str | None = None
    is_active: bool | None = None


class TeacherRead(TeacherBase, ApiModel):
    id: int
    created_at: datetime
    updated_at: datetime
