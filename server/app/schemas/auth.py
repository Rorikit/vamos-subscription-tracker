from datetime import datetime

from pydantic import BaseModel

from app.models.operator import OperatorRole
from app.schemas.common import ApiModel


class LoginRequest(ApiModel):
    username: str
    password: str


class OperatorRead(ApiModel):
    id: int
    username: str
    full_name: str
    role: OperatorRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OperatorCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: OperatorRole = OperatorRole.OPERATOR
    is_active: bool = True


class OperatorUpdate(BaseModel):
    username: str | None = None
    full_name: str | None = None
    password: str | None = None
    role: OperatorRole | None = None
    is_active: bool | None = None


class TokenResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    operator: OperatorRead
