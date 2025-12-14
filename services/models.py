from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Float, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class RawAPIRecord(Base):
    __tablename__ = "raw_api_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String, unique=True, nullable=False, index=True)
    payload = Column(Text, nullable=False)  # JSON stored as text
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RawCSVRecord(Base):
    __tablename__ = "raw_csv_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String, unique=True, nullable=False, index=True)
    payload = Column(Text, nullable=False)  # JSON stored as text
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class NormalizedRecord(Base):
    __tablename__ = "normalized_records"
    
    id = Column(String, primary_key=True)
    ticker = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    price_usd = Column(Float, nullable=False)
    market_cap_usd = Column(Float, nullable=True)
    volume_24h_usd = Column(Float, nullable=True)
    percent_change_24h = Column(Float, nullable=True)
    source = Column(String, nullable=False, index=True)
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
    source = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)  # success, failure, running
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    processed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
