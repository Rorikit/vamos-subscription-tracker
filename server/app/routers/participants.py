from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Participant
from app.schemas.participant import ParticipantCreate, ParticipantListItem, ParticipantRead, ParticipantUpdate
from app.services.memberships import get_active_membership

router = APIRouter(prefix="/participants", tags=["participants"])


@router.get("", response_model=list[ParticipantListItem])
def list_participants(search: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Participant)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(Participant.full_name.ilike(pattern) | Participant.phone.ilike(pattern))
    participants = query.order_by(Participant.full_name).all()
    result = []
    for participant in participants:
        active_membership = get_active_membership(db, participant.id)
        result.append(
            {
                "id": participant.id,
                "full_name": participant.full_name,
                "phone": participant.phone,
                "comment": participant.comment,
                "is_active": participant.is_active,
                "created_at": participant.created_at,
                "updated_at": participant.updated_at,
                "active_membership_id": active_membership.id if active_membership else None,
                "active_membership_status": active_membership.status.value if active_membership else None,
                "remaining_lessons": active_membership.remaining_lessons if active_membership else None,
                "end_date": active_membership.end_date.isoformat() if active_membership else None,
            }
        )
    return result


@router.get("/{participant_id}", response_model=ParticipantRead)
def get_participant(participant_id: int, db: Session = Depends(get_db)):
    participant = db.get(Participant, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
    return participant


@router.post("", response_model=ParticipantRead)
def create_participant(payload: ParticipantCreate, db: Session = Depends(get_db)):
    participant = Participant(**payload.model_dump())
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


@router.patch("/{participant_id}", response_model=ParticipantRead)
def update_participant(participant_id: int, payload: ParticipantUpdate, db: Session = Depends(get_db)):
    participant = db.get(Participant, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(participant, key, value)
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant
