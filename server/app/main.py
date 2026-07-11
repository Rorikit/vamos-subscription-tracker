from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.database import Base, SessionLocal, engine
from app.routers import auth, finance, membership_types, memberships, operators, participants, payments, teachers, visits
from app.seed import seed_data
from app.services.auth import ensure_default_operator, get_current_operator
from app.services.finance import ensure_teacher_seed

app = FastAPI(title="Vamos Subscription Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
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
        ensure_default_operator(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


def migrate_local_sqlite(db) -> None:
    inspector = inspect(engine)
    if "visits" not in inspector.get_table_names():
        return

    visit_columns = {column["name"] for column in inspector.get_columns("visits")}
    if "teacher_id" not in visit_columns:
        ensure_teacher_seed(db)
        teacher_id = db.execute(text("select id from teachers order by id limit 1")).scalar()
        db.execute(text("alter table visits add column teacher_id integer"))
        if teacher_id:
            db.execute(text("update visits set teacher_id = :teacher_id where teacher_id is null"), {"teacher_id": teacher_id})
        db.commit()
