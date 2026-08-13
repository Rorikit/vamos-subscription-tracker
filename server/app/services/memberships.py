from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import Membership, MembershipStatus, MembershipType, Participant, Teacher, Visit
from app.services.lesson_finance import calculate_visit_financials, quantize_money


def is_currently_active(membership: Membership) -> bool:
    return (
        membership.status == MembershipStatus.ACTIVE
        and membership.remaining_lessons > 0
        and membership.end_date >= date.today()
    )


def refresh_expired_status(db: Session, membership: Membership) -> Membership:
    if membership.status == MembershipStatus.ACTIVE and membership.end_date < date.today():
        membership.status = MembershipStatus.EXPIRED
        db.add(membership)
    return membership


def serialize_membership(db: Session, membership: Membership) -> dict:
    refresh_expired_status(db, membership)
    return {
        **membership.__dict__,
        "is_currently_active": is_currently_active(membership),
        "participant": membership.participant,
        "membership_type": membership.membership_type,
    }


def get_active_membership(db: Session, participant_id: int) -> Membership | None:
    memberships = (
        db.query(Membership)
        .options(joinedload(Membership.participant), joinedload(Membership.membership_type))
        .filter(Membership.participant_id == participant_id)
        .order_by(Membership.start_date.desc(), Membership.id.desc())
        .all()
    )
    for membership in memberships:
        refresh_expired_status(db, membership)
        if is_currently_active(membership):
            return membership
    db.commit()
    return None


def get_active_membership_by_type(db: Session, participant_id: int, membership_type_id: int) -> Membership | None:
    memberships = (
        db.query(Membership)
        .filter(Membership.participant_id == participant_id, Membership.membership_type_id == membership_type_id)
        .order_by(Membership.start_date.desc(), Membership.id.desc())
        .all()
    )
    for membership in memberships:
        refresh_expired_status(db, membership)
        if is_currently_active(membership):
            return membership
    db.commit()
    return None


def create_membership(db: Session, participant_id: int, membership_type_id: int, teacher_lesson_rate: Decimal | None = None) -> Membership:
    participant = db.get(Participant, participant_id)
    membership_type = db.get(MembershipType, membership_type_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
    if not membership_type or not membership_type.is_active:
        raise HTTPException(status_code=404, detail="Тип абонемента не найден или отключен")
    if membership_type.lesson_count <= 0:
        raise HTTPException(status_code=400, detail="В типе абонемента некорректное количество занятий")
    existing = get_active_membership_by_type(db, participant_id, membership_type_id)
    if existing:
        raise HTTPException(status_code=409, detail="У участника уже есть активный абонемент этого типа. Откройте редактирование текущего абонемента.")

    start = date.today()
    lesson_price = quantize_money(Decimal(membership_type.price) / Decimal(membership_type.lesson_count))
    rate = quantize_money(Decimal(teacher_lesson_rate) if teacher_lesson_rate is not None else lesson_price * Decimal("0.5"))
    if rate < 0:
        raise HTTPException(status_code=400, detail="Выплата преподавателю не может быть отрицательной")
    if rate > lesson_price:
        raise HTTPException(status_code=400, detail="Выплата преподавателю не может быть больше цены занятия")
    membership = Membership(
        participant_id=participant_id,
        membership_type_id=membership_type_id,
        total_lessons=membership_type.lesson_count,
        remaining_lessons=membership_type.lesson_count,
        price=membership_type.price,
        teacher_lesson_rate=rate,
        start_date=start,
        end_date=start + timedelta(days=membership_type.validity_days),
        status=MembershipStatus.ACTIVE,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def validate_membership_financials(membership: Membership) -> None:
    if membership.total_lessons <= 0:
        raise HTTPException(status_code=400, detail="В абонементе некорректное количество занятий")
    if membership.remaining_lessons < 0:
        raise HTTPException(status_code=400, detail="Остаток занятий не может быть отрицательным")
    if membership.remaining_lessons > membership.total_lessons:
        raise HTTPException(status_code=400, detail="Остаток занятий не может быть больше общего количества")
    if membership.end_date < membership.start_date:
        raise HTTPException(status_code=400, detail="Дата окончания должна быть позже даты начала")
    lesson_price = quantize_money(Decimal(membership.price) / Decimal(membership.total_lessons))
    rate = quantize_money(Decimal(membership.teacher_lesson_rate or 0))
    if rate > lesson_price:
        raise HTTPException(status_code=400, detail="Выплата преподавателю не может быть больше цены занятия")


def update_membership(db: Session, membership_id: int, data: dict) -> Membership:
    membership = db.get(Membership, membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    for key, value in data.items():
        setattr(membership, key, value)
    validate_membership_financials(membership)
    if membership.remaining_lessons == 0 and membership.status == MembershipStatus.ACTIVE:
        membership.status = MembershipStatus.FINISHED
    elif membership.remaining_lessons > 0 and membership.status == MembershipStatus.FINISHED and membership.end_date >= date.today():
        membership.status = MembershipStatus.ACTIVE
    refresh_expired_status(db, membership)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def create_visit_from_completed_lesson(
    db: Session,
    participant_id: int,
    membership_id: int | None,
    teacher_id: int,
    visit_date: date | None,
    commit: bool = True,
) -> Visit:
    teacher = db.get(Teacher, teacher_id)
    if not teacher or not teacher.is_active:
        raise HTTPException(status_code=400, detail="Активный преподаватель не найден")

    if membership_id:
        membership = db.get(Membership, membership_id)
        if not membership or membership.participant_id != participant_id:
            raise HTTPException(status_code=404, detail="Абонемент участника не найден")
        refresh_expired_status(db, membership)
        if not is_currently_active(membership):
            raise HTTPException(status_code=400, detail="Выбранный абонемент не активен")
    else:
        membership = get_active_membership(db, participant_id)
    if not membership:
        raise HTTPException(status_code=400, detail="У участника нет активного абонемента")
    if membership.status in {MembershipStatus.FROZEN, MembershipStatus.CANCELLED, MembershipStatus.EXPIRED}:
        raise HTTPException(status_code=400, detail="Абонемент нельзя использовать для проведения занятия")
    if membership.remaining_lessons <= 0:
        raise HTTPException(status_code=400, detail="Занятия закончились")

    financials = calculate_visit_financials(membership)
    visit = Visit(
        participant_id=participant_id,
        membership_id=membership.id,
        teacher_id=teacher_id,
        visit_date=visit_date or date.today(),
        lesson_price=financials["lesson_price"],
        teacher_lesson_rate=financials["teacher_lesson_rate"],
        teacher_earning=financials["teacher_earning"],
        school_earning=financials["school_earning"],
    )
    membership.remaining_lessons -= 1
    if membership.remaining_lessons == 0:
        membership.status = MembershipStatus.FINISHED
    db.add_all([visit, membership])
    if commit:
        db.commit()
        db.refresh(visit)
    else:
        db.flush()
    return visit


def cancel_visit(db: Session, visit_id: int, commit: bool = True) -> Visit:
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Списание не найдено")
    if visit.is_cancelled:
        raise HTTPException(status_code=400, detail="Занятие уже возвращено")

    membership = db.get(Membership, visit.membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Абонемент не найден")

    visit.is_cancelled = True
    membership.remaining_lessons += 1
    if membership.end_date < date.today():
        membership.status = MembershipStatus.EXPIRED
    elif membership.status == MembershipStatus.FINISHED:
        membership.status = MembershipStatus.ACTIVE
    db.add(membership)
    db.add(visit)
    if commit:
        db.commit()
        db.refresh(visit)
    else:
        db.flush()
    return visit


def change_status(db: Session, membership_id: int, status: MembershipStatus) -> Membership:
    membership = db.get(Membership, membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    membership.status = status
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def unfreeze(db: Session, membership_id: int) -> Membership:
    membership = db.get(Membership, membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    if membership.end_date < date.today():
        membership.status = MembershipStatus.EXPIRED
    elif membership.remaining_lessons <= 0:
        membership.status = MembershipStatus.FINISHED
    else:
        membership.status = MembershipStatus.ACTIVE
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership
