import os

from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.database import Base, SessionLocal, engine
from app.routers import auth, finance, membership_types, memberships, operators, participants, payments, teachers, visits
from app.seed import seed_data
from app.services.auth import ensure_default_operator, get_current_operator
from app.services.finance import ensure_teacher_seed
from app.services.lesson_finance import backfill_visit_financials

app = FastAPI(title="Vamos Subscription Tracker API")

default_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
extra_cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_cors_origins + extra_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

protected = [Depends(get_current_operator)]

app.include_router(auth.router)
app.include_router(participants.router, dependencies=protected)
app.include_router(membership_types.router, dependencies=protected)
app.include_router(memberships.router, dependencies=protected)
app.include_router(visits.router, dependencies=protected)
app.include_router(payments.router, dependencies=protected)
app.include_router(teachers.router, dependencies=protected)
app.include_router(operators.router, dependencies=protected)
app.include_router(finance.router, dependencies=protected)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        migrate_local_sqlite(db)
        seed_data(db)
        ensure_teacher_seed(db)
        backfill_visit_financials(db)
        ensure_default_operator(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


def migrate_local_sqlite(db) -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "teachers" in table_names:
        teacher_columns = {column["name"] for column in inspector.get_columns("teachers")}
        if "teacher_share_percent" not in teacher_columns:
            db.execute(text("alter table teachers add column teacher_share_percent numeric(5, 2) default 50"))
            db.execute(text("update teachers set teacher_share_percent = 50 where teacher_share_percent is null"))
            db.commit()

    if "visits" not in table_names:
        return

    visit_columns = {column["name"] for column in inspector.get_columns("visits")}
    if "teacher_id" not in visit_columns:
        ensure_teacher_seed(db)
        teacher_id = db.execute(text("select id from teachers order by id limit 1")).scalar()
        db.execute(text("alter table visits add column teacher_id integer"))
        if teacher_id:
            db.execute(text("update visits set teacher_id = :teacher_id where teacher_id is null"), {"teacher_id": teacher_id})
        db.commit()

    inspector = inspect(engine)
    visit_columns = {column["name"] for column in inspector.get_columns("visits")}
    visit_finance_columns = {
        "lesson_price": "numeric(10, 2)",
        "teacher_share_percent": "numeric(5, 2)",
        "teacher_earning": "numeric(10, 2)",
        "school_earning": "numeric(10, 2)",
    }
    for column_name, column_type in visit_finance_columns.items():
        if column_name not in visit_columns:
            db.execute(text(f"alter table visits add column {column_name} {column_type}"))
    db.commit()

    backfill_visit_financials(db)
