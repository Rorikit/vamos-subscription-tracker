from datetime import datetime

from app.schemas.common import ApiModel


class AuditLogRead(ApiModel):
    id: int
    operator_id: int | None = None
    operator_name: str | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    entity_label: str | None = None
    before_json: str | None = None
    after_json: str | None = None
    created_at: datetime
