from __future__ import annotations

import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AttendanceStatus,
    Participant,
    ScheduleEvent,
    ScheduleEventParticipant,
    ScheduleEventStatus,
    ScheduleEventType,
    Teacher,
)
from app.schemas.schedule import ScheduleEventCreate, ScheduleEventUpdate
from app.services.memberships import cancel_visit, create_visit_from_completed_lesson
from app.services.schedule_conflicts import find_teacher_conflicts
from app.services.schedule_recurrence import generate_occurrences, make_recurrence_group_id, normalize_recurrence_rule


def event_query(db: Session):
    return db.query(ScheduleEvent).options(
        joinedload(ScheduleEvent.teacher),
        joinedload(ScheduleEvent.participants).joinedload(ScheduleEventParticipant.participant),
        joinedload(ScheduleEvent.participants).joinedload(ScheduleEventParticipant.visit),
    )


def list_events(
    db: Session,
    date_from: datetime,
    date_to: datetime,
    teacher_id: int | None = None,
    participant_id: int | None = None,
    status: ScheduleEventStatus | None = None,
    event_type: ScheduleEventType | None = None,
) -> list[ScheduleEvent]:
    query = event_query(db).filter(ScheduleEvent.starts_at < date_to, ScheduleEvent.ends_at > date_from)
    if teacher_id:
        query = query.filter(ScheduleEvent.teacher_id == teacher_id)
    if status:
        query = query.filter(ScheduleEvent.status == status)
    if event_type:
        query = query.filter(ScheduleEvent.event_type == event_type)
    if participant_id:
        query = query.join(ScheduleEventParticipant).filter(ScheduleEventParticipant.participant_id == participant_id)
    return query.order_by(ScheduleEvent.starts_at, ScheduleEvent.id).all()


def get_event(db: Session, event_id: int) -> ScheduleEvent:
    event = event_query(db).filter(ScheduleEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Занятие не найдено")
    return event


def create_events(db: Session, payload: ScheduleEventCreate) -> list[ScheduleEvent]:
    validate_event_payload(db, payload.teacher_id, payload.starts_at, payload.ends_at, payload.event_type, payload.participant_ids)
    rule = normalize_recurrence_rule(payload.recurrence)
    occurrences = generate_occurrences(payload.starts_at, payload.ends_at, rule)
    recurrence_group_id = make_recurrence_group_id() if len(occurrences) > 1 else None
    recurrence_rule = json.dumps(rule, ensure_ascii=False) if rule else None

    events: list[ScheduleEvent] = []
    for starts_at, ends_at in occurrences:
        conflicts = find_teacher_conflicts(db, payload.teacher_id, starts_at, ends_at)
        if conflicts:
            raise_conflict(conflicts[0])
        event = ScheduleEvent(
            title=payload.title.strip(),
            description=payload.description,
            teacher_id=payload.teacher_id,
            starts_at=starts_at,
            ends_at=ends_at,
            event_type=payload.event_type,
            location=payload.location,
            color=payload.color,
            recurrence_group_id=recurrence_group_id,
            recurrence_rule=recurrence_rule,
        )
        event.participants = [
            ScheduleEventParticipant(participant_id=participant_id, attendance_status=AttendanceStatus.PLANNED)
            for participant_id in payload.participant_ids
        ]
        db.add(event)
        events.append(event)

    db.commit()
    for event in events:
        db.refresh(event)
    return events


def update_event(db: Session, event_id: int, payload: ScheduleEventUpdate) -> ScheduleEvent:
    event = get_event(db, event_id)
    if event.status != ScheduleEventStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="Можно редактировать только запланированное занятие")

    data = payload.model_dump(exclude_unset=True)
    participant_ids = data.pop("participant_ids", None)
    data.pop("scope", None)
    next_teacher_id = data.get("teacher_id", event.teacher_id)
    next_starts_at = data.get("starts_at", event.starts_at)
    next_ends_at = data.get("ends_at", event.ends_at)
    next_event_type = data.get("event_type", event.event_type)
    validate_event_payload(db, next_teacher_id, next_starts_at, next_ends_at, next_event_type, participant_ids)
    conflicts = find_teacher_conflicts(db, next_teacher_id, next_starts_at, next_ends_at, exclude_event_id=event.id)
    if conflicts:
        raise_conflict(conflicts[0])

    for key, value in data.items():
        setattr(event, key, value)
    if participant_ids is not None:
        sync_event_participants(event, participant_ids)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def move_event(db: Session, event_id: int, starts_at: datetime, ends_at: datetime, scope: str = "single") -> ScheduleEvent:
    event = get_event(db, event_id)
    if event.status != ScheduleEventStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="Можно переносить только запланированное занятие")
    validate_time_range(starts_at, ends_at)
    conflicts = find_teacher_conflicts(db, event.teacher_id, starts_at, ends_at, exclude_event_id=event.id)
    if conflicts:
        raise_conflict(conflicts[0])
    event.starts_at = starts_at
    event.ends_at = ends_at
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def cancel_event(db: Session, event_id: int) -> ScheduleEvent:
    event = get_event(db, event_id)
    if event.status == ScheduleEventStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Проведенное занятие нельзя отменить")
    if event.status != ScheduleEventStatus.CANCELLED:
        event.status = ScheduleEventStatus.CANCELLED
        event.cancelled_at = datetime.utcnow()
        for participant in event.participants:
            participant.attendance_status = AttendanceStatus.CANCELLED
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: int) -> ScheduleEvent:
    event = get_event(db, event_id)
    if any(participant.visit_id for participant in event.participants):
        raise HTTPException(status_code=400, detail="Нельзя удалить занятие с проведенными посещениями. Сначала верните занятия участникам.")
    if event.status == ScheduleEventStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Проведенное занятие нельзя удалить")
    db.delete(event)
    db.commit()
    return event


def add_participant(db: Session, event_id: int, participant_id: int) -> ScheduleEvent:
    event = get_event(db, event_id)
    if event.status != ScheduleEventStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="Участников можно менять только до проведения занятия")
    ensure_participants_exist(db, [participant_id])
    if any(item.participant_id == participant_id for item in event.participants):
        raise HTTPException(status_code=400, detail="Участник уже добавлен в занятие")
    event.participants.append(ScheduleEventParticipant(participant_id=participant_id))
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def remove_participant(db: Session, event_id: int, participant_id: int) -> ScheduleEvent:
    event = get_event(db, event_id)
    if event.status != ScheduleEventStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="Участников можно менять только до проведения занятия")
    item = next((participant for participant in event.participants if participant.participant_id == participant_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Участник не найден в занятии")
    db.delete(item)
    db.commit()
    db.refresh(event)
    return event


def complete_event(db: Session, event_id: int, attendance: list[dict]) -> ScheduleEvent:
    event = get_event(db, event_id)
    if event.status == ScheduleEventStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Занятие уже проведено")
    if event.status == ScheduleEventStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Отмененное занятие нельзя провести")
    attendance_by_participant = {item["participant_id"]: item["attendance_status"] for item in attendance}
    participant_ids = {item.participant_id for item in event.participants}
    if set(attendance_by_participant) - participant_ids:
        raise HTTPException(status_code=400, detail="В проведении есть участник, которого нет в занятии")

    try:
        for item in event.participants:
            status = attendance_by_participant.get(item.participant_id, AttendanceStatus.ATTENDED)
            if item.visit_id:
                raise HTTPException(status_code=400, detail="Для участника уже создано списание")
            item.attendance_status = status
            if status == AttendanceStatus.ATTENDED:
                visit = create_visit_from_completed_lesson(db, item.participant_id, None, event.teacher_id, event.starts_at.date(), commit=False)
                item.visit_id = visit.id
            db.add(item)
        event.status = ScheduleEventStatus.COMPLETED
        event.completed_at = datetime.utcnow()
        db.add(event)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(event)
    return event


def return_participant_visit(db: Session, event_id: int, participant_id: int) -> ScheduleEvent:
    event = get_event(db, event_id)
    item = next((participant for participant in event.participants if participant.participant_id == participant_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Участник не найден в занятии")
    if not item.visit_id:
        raise HTTPException(status_code=400, detail="У участника нет связанного списания")
    cancel_visit(db, item.visit_id, commit=False)
    item.attendance_status = AttendanceStatus.REFUNDED
    db.add(item)
    db.commit()
    db.refresh(event)
    return event


def validate_event_payload(
    db: Session,
    teacher_id: int,
    starts_at: datetime,
    ends_at: datetime,
    event_type: ScheduleEventType,
    participant_ids: list[int] | None,
) -> None:
    validate_time_range(starts_at, ends_at)
    teacher = db.get(Teacher, teacher_id)
    if not teacher or not teacher.is_active:
        raise HTTPException(status_code=400, detail="Активный преподаватель не найден")
    if participant_ids is None:
        return
    if len(participant_ids) != len(set(participant_ids)):
        raise HTTPException(status_code=400, detail="Участник не может быть добавлен дважды")
    if event_type in {ScheduleEventType.GROUP, ScheduleEventType.INDIVIDUAL} and not participant_ids:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одного участника")
    ensure_participants_exist(db, participant_ids)


def validate_time_range(starts_at: datetime, ends_at: datetime) -> None:
    if ends_at <= starts_at:
        raise HTTPException(status_code=400, detail="Время окончания должно быть позже начала")


def ensure_participants_exist(db: Session, participant_ids: list[int]) -> None:
    if not participant_ids:
        return
    existing = {participant.id for participant in db.query(Participant).filter(Participant.id.in_(participant_ids)).all()}
    missing = set(participant_ids) - existing
    if missing:
        raise HTTPException(status_code=404, detail=f"Участники не найдены: {', '.join(map(str, sorted(missing)))}")


def sync_event_participants(event: ScheduleEvent, participant_ids: list[int]) -> None:
    next_ids = set(participant_ids)
    event.participants[:] = [item for item in event.participants if item.participant_id in next_ids]
    existing_ids = {item.participant_id for item in event.participants}
    for participant_id in participant_ids:
        if participant_id not in existing_ids:
            event.participants.append(
                ScheduleEventParticipant(participant_id=participant_id, attendance_status=AttendanceStatus.PLANNED)
            )
            existing_ids.add(participant_id)


def raise_conflict(event: ScheduleEvent) -> None:
    raise HTTPException(
        status_code=409,
        detail=f"Конфликт расписания: {event.teacher.full_name if event.teacher else 'преподаватель'} занят на событии «{event.title}»",
    )
