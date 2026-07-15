import os

from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.database import Base, SessionLocal, engine
from app.models import Membership, MembershipType, Participant, Payment, Teacher, Visit
from app.routers import audit_logs, auth, finance, membership_types, memberships, operators, participants, payments, teachers, visits
from app.seed import seed_data
from app.services.auth import ensure_default_operator, ensure_system_operator, get_current_operator
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
app.include_router(audit_logs.router, dependencies=protected)
app.include_router(participants.router, dependencies=protected)
app.include_router(membership_types.router, dependencies=protected)
app.include_router(memberships.router, dependencies=protected)
app.include_router(visits.router, dependencies=protected)
app.include_router(payments.router, dependencies=protected)
app.include_router(teachers.router, dependencies=protected)
app.include_router(operators.router, dependencies=protected)
app.include_router(finance.router, dependencies=protected)


def should_seed_demo_data() -> bool:
    return os.getenv("SEED_DEMO_DATA", "true").strip().lower() in {"1", "true", "yes", "on"}


def remove_demo_seed_data(db) -> None:
    demo_participant_phones = {
        "+7 900 111-22-33",
        "+7 900 222-33-44",
        "+7 900 333-44-55",
        "+7 900 444-55-66",
        "+7 900 555-66-77",
    }
    demo_teacher_phones = {
        "+7 901 100-10-10",
        "+7 901 200-20-20",
        "+7 901 300-30-30",
    }
    demo_type_names = {"Старт 4", "База 8", "Интенсив 12"}

    participant_phones = {phone for (phone,) in db.query(Participant.phone).all()}
    teacher_phones = {phone for (phone,) in db.query(Teacher.phone).all()}
    type_names = {name for (name,) in db.query(MembershipType.name).all()}
    has_only_demo_data = (
        db.query(Participant).count() == len(demo_participant_phones)
        and db.query(Teacher).count() == len(demo_teacher_phones)
        and db.query(MembershipType).count() == len(demo_type_names)
        and participant_phones == demo_participant_phones
        and teacher_phones == demo_teacher_phones
        and type_names == demo_type_names
    )

    if not has_only_demo_data:
        return

    db.query(Visit).delete()
    db.query(Payment).delete()
    db.query(Membership).delete()
    db.query(Participant).delete()
    db.query(MembershipType).delete()
    db.query(Teacher).delete()
    db.commit()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        migrate_local_sqlite(db)
        if should_seed_demo_data():
            seed_data(db)
            ensure_teacher_seed(db)
        else:
            remove_demo_seed_data(db)
        backfill_visit_financials(db)
        ensure_default_operator(db)
        ensure_system_operator(db)
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

    if "operators" in table_names:
        operator_columns = {column["name"] for column in inspector.get_columns("operators")}
        if "role" not in operator_columns:
            db.execute(text("alter table operators add column role varchar(8) default 'ADMIN'"))
            db.execute(text("update operators set role = 'ADMIN' where role is null"))
            db.commit()

    if "memberships" in table_names:
        membership_columns = {column["name"] for column in inspector.get_columns("memberships")}
        if "teacher_lesson_rate" not in membership_columns:
            db.execute(text("alter table memberships add column teacher_lesson_rate numeric(10, 2) default 0"))
            db.execute(
                text(
                    """
                    update memberships
                    set teacher_lesson_rate = round((price / total_lessons) * 0.5, 2)
                    where total_lessons > 0 and (teacher_lesson_rate is null or teacher_lesson_rate = 0)
                    """
                )
            )
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
        "teacher_lesson_rate": "numeric(10, 2)",
        "teacher_share_percent": "numeric(5, 2)",
        "teacher_earning": "numeric(10, 2)",
        "school_earning": "numeric(10, 2)",
    }
    for column_name, column_type in visit_finance_columns.items():
        if column_name not in visit_columns:
            db.execute(text(f"alter table visits add column {column_name} {column_type}"))
    db.commit()
    db.execute(text("update visits set teacher_lesson_rate = teacher_earning where teacher_lesson_rate is null and teacher_earning is not null"))
    db.commit()

    backfill_visit_financials(db)
