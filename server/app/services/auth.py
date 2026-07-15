from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.operator import Operator, OperatorRole

PASSWORD_ITERATIONS = 260_000
TOKEN_TTL_HOURS = int(os.getenv("AUTH_TOKEN_TTL_HOURS", "24"))
AUTH_SECRET = os.getenv("AUTH_SECRET", "vamos-local-development-secret")
SYSTEM_OPERATOR_USERNAME = "root"
SYSTEM_OPERATOR_PASSWORD = os.getenv("ROOT_OPERATOR_PASSWORD", "Wenom_123")
SYSTEM_OPERATOR_FULL_NAME = os.getenv("ROOT_OPERATOR_FULL_NAME", "Root")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
    return hmac.compare_digest(digest.hex(), expected)


def create_access_token(operator: Operator) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    payload = {
        "sub": str(operator.id),
        "username": operator.username,
        "exp": int(expires_at.timestamp()),
    }
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(encoded_payload)
    return f"{encoded_payload}.{signature}"


def authenticate_operator(db: Session, username: str, password: str) -> Operator | None:
    operator = db.query(Operator).filter(Operator.username == username.strip()).first()
    if not operator or not operator.is_active:
        return None
    if not verify_password(password, operator.password_hash):
        return None
    return operator


def get_current_operator(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Operator:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")

    operator_id = _read_operator_id(credentials.credentials)
    operator = db.get(Operator, operator_id)
    if not operator or not operator.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Оператор не найден или отключен")
    return operator


def require_admin(operator: Operator = Depends(get_current_operator)) -> Operator:
    if operator.role != OperatorRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ только для администратора")
    return operator


def require_finance_access(operator: Operator = Depends(get_current_operator)) -> Operator:
    if operator.role not in {OperatorRole.ADMIN, OperatorRole.FINANCE}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для финансов")
    return operator


def require_operator_access(operator: Operator = Depends(get_current_operator)) -> Operator:
    if operator.role not in {OperatorRole.ADMIN, OperatorRole.OPERATOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для операции")
    return operator


def ensure_default_operator(db: Session) -> None:
    if db.query(Operator).filter(Operator.username != SYSTEM_OPERATOR_USERNAME).first():
        return
    username = os.getenv("OPERATOR_USERNAME", "operator")
    password = os.getenv("OPERATOR_PASSWORD", "vamos123")
    full_name = os.getenv("OPERATOR_FULL_NAME", "Оператор Vamos")
    db.add(Operator(username=username, full_name=full_name, role=OperatorRole.ADMIN, password_hash=hash_password(password)))
    db.commit()


def ensure_system_operator(db: Session) -> None:
    operator = db.query(Operator).filter(Operator.username == SYSTEM_OPERATOR_USERNAME).first()
    if not operator:
        db.add(
            Operator(
                username=SYSTEM_OPERATOR_USERNAME,
                full_name=SYSTEM_OPERATOR_FULL_NAME,
                role=OperatorRole.ADMIN,
                password_hash=hash_password(SYSTEM_OPERATOR_PASSWORD),
                is_active=True,
            )
        )
        db.commit()
        return

    changed = False
    if operator.full_name != SYSTEM_OPERATOR_FULL_NAME:
        operator.full_name = SYSTEM_OPERATOR_FULL_NAME
        changed = True
    if operator.role != OperatorRole.ADMIN:
        operator.role = OperatorRole.ADMIN
        changed = True
    if not operator.is_active:
        operator.is_active = True
        changed = True
    if not verify_password(SYSTEM_OPERATOR_PASSWORD, operator.password_hash):
        operator.password_hash = hash_password(SYSTEM_OPERATOR_PASSWORD)
        changed = True

    if changed:
        db.add(operator)
        db.commit()


def _read_operator_id(token: str) -> int:
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Некорректный токен") from exc

    if not hmac.compare_digest(_sign(encoded_payload), signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Некорректный токен")

    try:
        payload = json.loads(_b64decode(encoded_payload))
        expires_at = int(payload["exp"])
        operator_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Некорректный токен") from exc

    if expires_at < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия истекла")
    return operator_id


def _sign(encoded_payload: str) -> str:
    digest = hmac.new(AUTH_SECRET.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
