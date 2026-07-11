from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.operator import Operator
from app.schemas.auth import OperatorCreate, OperatorRead, OperatorUpdate
from app.services.auth import get_current_operator, hash_password

router = APIRouter(prefix="/operators", tags=["operators"])


@router.get("", response_model=list[OperatorRead])
def list_operators(db: Session = Depends(get_db)):
    return db.query(Operator).order_by(Operator.full_name).all()


@router.get("/{operator_id}", response_model=OperatorRead)
def get_operator(operator_id: int, db: Session = Depends(get_db)):
    operator = db.get(Operator, operator_id)
    if not operator:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return operator


@router.post("", response_model=OperatorRead, status_code=status.HTTP_201_CREATED)
def create_operator(payload: OperatorCreate, db: Session = Depends(get_db)):
    username = payload.username.strip()
    if db.query(Operator).filter(Operator.username == username).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

    operator = Operator(
        username=username,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
    )
    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator


@router.patch("/{operator_id}", response_model=OperatorRead)
def update_operator(
    operator_id: int,
    payload: OperatorUpdate,
    db: Session = Depends(get_db),
    current_operator: Operator = Depends(get_current_operator),
):
    operator = db.get(Operator, operator_id)
    if not operator:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    data = payload.model_dump(exclude_unset=True)
    if "username" in data and data["username"] is not None:
        username = data["username"].strip()
        existing = db.query(Operator).filter(Operator.username == username, Operator.id != operator_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
        operator.username = username
    if "full_name" in data and data["full_name"] is not None:
        operator.full_name = data["full_name"].strip()
    if "password" in data and data["password"]:
        operator.password_hash = hash_password(data["password"])
    if "is_active" in data and data["is_active"] is not None:
        if operator.id == current_operator.id and data["is_active"] is False:
            raise HTTPException(status_code=400, detail="Нельзя отключить текущего пользователя")
        operator.is_active = data["is_active"]

    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator
