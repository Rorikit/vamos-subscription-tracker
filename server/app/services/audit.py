from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, Operator


def log_action(
    db: Session,
    operator: Operator | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    entity_label: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    log = AuditLog(
        operator_id=operator.id if operator else None,
        operator_name=operator.full_name if operator else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        before_json=_to_json(before),
        after_json=_to_json(after),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def snapshot(obj: Any, fields: list[str]) -> dict[str, Any]:
    return {field: _jsonable(getattr(obj, field, None)) for field in fields}


def _to_json(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    return value
