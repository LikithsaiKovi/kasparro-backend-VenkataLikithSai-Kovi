from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RawAPIRecord(Base):
    __tablename__ = "raw_api_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("external_id", name="uq_raw_api_external_id"),)


class RawCSVRecord(Base):
    __tablename__ = "raw_csv_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("external_id", name="uq_raw_csv_external_id"),)


class NormalizedRecord(Base):
    __tablename__ = "normalized_records"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ETLCheckpoint(Base):
    __tablename__ = "etl_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, unique=True, nullable=False)
    last_id = Column(String, nullable=True)
    last_timestamp = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ETLRun(Base):
    __tablename__ = "etl_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    message = Column(String, nullable=True)
    processed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)
    __table_args__ = (UniqueConstraint("id", "source", name="uq_run"),)

