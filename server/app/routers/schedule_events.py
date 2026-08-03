from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Operator, ScheduleEventStatus, ScheduleEventType
from app.schemas.schedule import (
    ScheduleConflictRead,
    ScheduleEventComplete,
    ScheduleEventCreate,
    ScheduleEventMove,
    ScheduleEventParticipantAdd,
    ScheduleEventRead,
    ScheduleEventUpdate,
)
from app.services.audit import log_action, snapshot
from app.services.auth import require_operator_access
from app.services.schedule_conflicts import find_teacher_conflicts, serialize_conflict
from app.services.schedule_events import (
    add_participant,
    cancel_event,
    complete_event,
    create_events,
    get_event,
    list_events,
    move_event,
    remove_participant,
    return_participant_visit,
    update_event,
)

router = APIRouter(prefix="/schedule-events", tags=["schedule-events"])


@router.get("", response_model=list[ScheduleEventRead])
def list_schedule_events(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    teacher_id: int | None = None,
    participant_id: int | None = None,
    status: ScheduleEventStatus | None = None,
    event_type: ScheduleEventType | None = None,
    db: Session = Depends(get_db),
):
    start = date_from or datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = date_to or start + timedelta(days=31)
    return list_events(db, start, end, teacher_id, participant_id, status, event_type)


@router.get("/conflicts", response_model=list[ScheduleConflictRead])
def schedule_conflicts(
    teacher_id: int,
    starts_at: datetime,
    ends_at: datetime,
    exclude_event_id: int | None = None,
    db: Session = Depends(get_db),
):
    return [serialize_conflict(event) for event in find_teacher_conflicts(db, teacher_id, starts_at, ends_at, exclude_event_id)]


@router.get("/{event_id}", response_model=ScheduleEventRead)
def get_schedule_event(event_id: int, db: Session = Depends(get_db)):
    return get_event(db, event_id)


@router.post("", response_model=list[ScheduleEventRead])
def create_schedule_event(
    payload: ScheduleEventCreate,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_operator_access),
):
    events = create_events(db, payload)
    log_action(db, operator, "schedule_event_created", "schedule_event", events[0].id, events[0].title, after={"count": len(events)})
    return events


@router.patch("/{event_id}", response_model=ScheduleEventRead)
def patch_schedule_event(
    event_id: int,
    payload: ScheduleEventUpdate,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_operator_access),
):
    before = snapshot(get_event(db, event_id), ["title", "teacher_id", "starts_at", "ends_at", "status", "event_type"])
    event = update_event(db, event_id, payload)
    log_action(db, operator, "schedule_event_updated", "schedule_event", event.id, event.title, before=before, after=snapshot(event, ["title", "teacher_id", "starts_at", "ends_at", "status", "event_type"]))
    return event


@router.post("/{event_id}/cancel", response_model=ScheduleEventRead)
def cancel_schedule_event(
    event_id: int,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_operator_access),
):
    event = cancel_event(db, event_id)
    log_action(db, operator, "schedule_event_cancelled", "schedule_event", event.id, event.title, after=snapshot(event, ["status", "cancelled_at"]))
    return event


@router.post("/{event_id}/move", response_model=ScheduleEventRead)
def move_schedule_event(
    event_id: int,
    payload: ScheduleEventMove,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_operator_access),
):
    event = move_event(db, event_id, payload.starts_at, payload.ends_at, payload.scope)
    log_action(db, operator, "schedule_event_moved", "schedule_event", event.id, event.title, after=snapshot(event, ["starts_at", "ends_at"]))
    return event


@router.post("/{event_id}/complete", response_model=ScheduleEventRead)
def complete_schedule_event(
    event_id: int,
    payload: ScheduleEventComplete,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_operator_access),
):
    event = complete_event(db, event_id, [item.model_dump() for item in payload.participants])
    log_action(db, operator, "schedule_event_completed", "schedule_event", event.id, event.title, after=snapshot(event, ["status", "completed_at"]))
    return event


@router.post("/{event_id}/participants", response_model=ScheduleEventRead)
def add_schedule_event_participant(
    event_id: int,
    payload: ScheduleEventParticipantAdd,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_operator_access),
):
    event = add_participant(db, event_id, payload.participant_id)
    log_action(db, operator, "schedule_event_participant_added", "schedule_event", event.id, event.title, after={"participant_id": payload.participant_id})
    return event


@router.delete("/{event_id}/participants/{participant_id}", response_model=ScheduleEventRead)
def remove_schedule_event_participant(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_operator_access),
):
    event = remove_participant(db, event_id, participant_id)
    log_action(db, operator, "schedule_event_participant_removed", "schedule_event", event.id, event.title, after={"participant_id": participant_id})
    return event


@router.post("/{event_id}/participants/{participant_id}/return", response_model=ScheduleEventRead)
def return_schedule_event_participant(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_operator_access),
):
    event = return_participant_visit(db, event_id, participant_id)
    log_action(db, operator, "schedule_event_participant_returned", "schedule_event", event.id, event.title, after={"participant_id": participant_id})
    return event
