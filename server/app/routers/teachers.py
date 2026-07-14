from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Operator, Teacher
from app.schemas.teacher import TeacherCreate, TeacherRead, TeacherUpdate
from app.services.audit import log_action, snapshot
from app.services.auth import require_admin

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("", response_model=list[TeacherRead])
def list_teachers(db: Session = Depends(get_db)):
    return db.query(Teacher).order_by(Teacher.full_name).all()


@router.get("/{teacher_id}", response_model=TeacherRead)
def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Преподаватель не найден")
    return teacher


@router.post("", response_model=TeacherRead)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    teacher = Teacher(**payload.model_dump())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    log_action(db, operator, "teacher_created", "teacher", teacher.id, teacher.full_name, after=snapshot(teacher, ["full_name", "phone", "teacher_share_percent", "is_active"]))
    return teacher


@router.patch("/{teacher_id}", response_model=TeacherRead)
def update_teacher(teacher_id: int, payload: TeacherUpdate, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Преподаватель не найден")
    before = snapshot(teacher, ["full_name", "phone", "comment", "teacher_share_percent", "is_active"])
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(teacher, key, value)
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    log_action(db, operator, "teacher_updated", "teacher", teacher.id, teacher.full_name, before=before, after=snapshot(teacher, ["full_name", "phone", "comment", "teacher_share_percent", "is_active"]))
    return teacher
