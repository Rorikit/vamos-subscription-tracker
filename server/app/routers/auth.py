from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.operator import Operator
from app.schemas.auth import LoginRequest, OperatorRead, TokenResponse
from app.services.auth import authenticate_operator, create_access_token, get_current_operator

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    operator = authenticate_operator(db, payload.username, payload.password)
    if not operator:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    return TokenResponse(access_token=create_access_token(operator), operator=operator)


@router.get("/me", response_model=OperatorRead)
def me(operator: Operator = Depends(get_current_operator)):
    return operator
