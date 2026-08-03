from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException

MAX_RECURRENCE_EVENTS = 365


def make_recurrence_group_id() -> str:
    return uuid4().hex


def normalize_recurrence_rule(rule: dict | None) -> dict | None:
    if not rule or rule.get("frequency") in {None, "", "none"}:
        return None

    frequency = rule.get("frequency")
    if frequency not in {"daily", "weekly", "weekdays", "n_weeks"}:
        raise HTTPException(status_code=400, detail="Неподдерживаемое повторение")

    count = int(rule.get("count") or 0)
    until = rule.get("until")
    interval = max(1, int(rule.get("interval") or 1))
    weekdays = [int(day) for day in rule.get("weekdays", [])]

    if count <= 0 and not until:
        raise HTTPException(status_code=400, detail="Укажите количество повторов или дату окончания")
    if count > MAX_RECURRENCE_EVENTS:
        raise HTTPException(status_code=400, detail=f"Серия не может быть больше {MAX_RECURRENCE_EVENTS} занятий")
    if frequency == "weekdays" and not weekdays:
        raise HTTPException(status_code=400, detail="Выберите дни недели для повторения")

    return {
        "frequency": frequency,
        "count": count or None,
        "until": until or None,
        "interval": interval,
        "weekdays": sorted(set(weekdays)),
    }


def generate_occurrences(starts_at: datetime, ends_at: datetime, rule: dict | None) -> list[tuple[datetime, datetime]]:
    normalized = normalize_recurrence_rule(rule)
    if not normalized:
        return [(starts_at, ends_at)]

    duration = ends_at - starts_at
    until = datetime.fromisoformat(normalized["until"]) if normalized["until"] else None
    count = normalized["count"] or MAX_RECURRENCE_EVENTS
    frequency = normalized["frequency"]
    interval = normalized["interval"]
    weekdays = set(normalized["weekdays"])

    occurrences: list[tuple[datetime, datetime]] = []
    cursor = starts_at
    attempts = 0
    while len(occurrences) < count and len(occurrences) < MAX_RECURRENCE_EVENTS:
        attempts += 1
        if attempts > MAX_RECURRENCE_EVENTS * 14:
            break

        should_include = False
        if frequency == "daily":
            should_include = True
        elif frequency in {"weekly", "n_weeks"}:
            weeks_delta = (cursor.date() - starts_at.date()).days // 7
            should_include = cursor.weekday() == starts_at.weekday() and weeks_delta % interval == 0
        elif frequency == "weekdays":
            should_include = cursor.weekday() in weekdays

        if should_include:
            if until and cursor > until:
                break
            occurrences.append((cursor, cursor + duration))

        cursor += timedelta(days=1)

    if not occurrences:
        raise HTTPException(status_code=400, detail="Не удалось сформировать серию занятий")
    return occurrences
