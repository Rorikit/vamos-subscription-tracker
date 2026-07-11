from datetime import datetime

from app.schemas.common import ApiModel


class LoginRequest(ApiModel):
    username: str
    password: str


class OperatorRead(ApiModel):
    id: int
    username: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    operator: OperatorRead
