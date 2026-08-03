from datetime import datetime

from sqlalchemy.orm import Session

from app.models import ScheduleEvent, ScheduleEventStatus


def find_teacher_conflicts(
    db: Session,
    teacher_id: int,
    starts_at: datetime,
    ends_at: datetime,
    exclude_event_id: int | None = None,
) -> list[ScheduleEvent]:
    query = db.query(ScheduleEvent).filter(
        ScheduleEvent.teacher_id == teacher_id,
        ScheduleEvent.status != ScheduleEventStatus.CANCELLED,
        ScheduleEvent.starts_at < ends_at,
        ScheduleEvent.ends_at > starts_at,
    )
    if exclude_event_id:
        query = query.filter(ScheduleEvent.id != exclude_event_id)
    return query.order_by(ScheduleEvent.starts_at).all()


def serialize_conflict(event: ScheduleEvent) -> dict:
    return {
        "event_id": event.id,
        "title": event.title,
        "teacher_name": event.teacher.full_name if event.teacher else None,
        "starts_at": event.starts_at,
        "ends_at": event.ends_at,
    }
