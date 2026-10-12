from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, LargeBinary, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class LegacyBatch(Base):
    __tablename__ = "legacy_batches"
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    summary_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class LegacySource(Base):
    __tablename__ = "legacy_sources"
    source_key: Mapped[str] = mapped_column(String(40), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(ForeignKey("legacy_batches.fingerprint"))
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    metadata_json: Mapped[str] = mapped_column(Text)
    original_blob: Mapped[bytes] = mapped_column(LargeBinary)
    standardized_blob: Mapped[bytes] = mapped_column(LargeBinary)

class LegacySheet(Base):
    __tablename__ = "legacy_sheets"
    __table_args__ = (UniqueConstraint("source_key", "sheet_index"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(ForeignKey("legacy_sources.source_key"), index=True)
    sheet_index: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    proposed_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cell_count: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[str] = mapped_column(Text)
    cells_compressed: Mapped[bytes] = mapped_column(LargeBinary)

class LegacyRecord(Base):
    __tablename__ = "legacy_records"
    record_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_key: Mapped[str] = mapped_column(ForeignKey("legacy_sources.source_key"), index=True)
    sheet_index: Mapped[int] = mapped_column(Integer)
    sheet_name: Mapped[str] = mapped_column(String(255))
    row: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    date: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(20), default="review", index=True)
    payload_json: Mapped[str] = mapped_column(Text)

class LegacyPerson(Base):
    __tablename__ = "legacy_people"
    __table_args__ = (UniqueConstraint("role", "label"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    label: Mapped[str] = mapped_column(String(255))
    variants_json: Mapped[str] = mapped_column(Text)
    product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution: Mapped[str] = mapped_column(String(40))
