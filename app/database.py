"""Database layer (PostgreSQL via pgAdmin4 / local server, with SQLite fallback).

Settings are read from a `.env` file in the project root (copy `.env.example` to `.env`):
    DB_TYPE=postgres          # postgres | sqlite
    DB_HOST=localhost
    DB_PORT=5433
    DB_NAME=fx_dashboard
    DB_USER=postgres
    DB_PASSWORD=seph7303
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (Boolean, Column, Date, Float, Integer, String, UniqueConstraint,
                        create_engine, text)
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DB_TYPE = os.getenv("DB_TYPE", "postgres").lower()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "fx_dashboard")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "seph7303")


def _pg_url(database: str) -> URL:
    # URL.create escapes special characters (@ : / #) in the password safely
    return URL.create("postgresql+psycopg2", username=DB_USER, password=DB_PASSWORD,
                      host=DB_HOST, port=DB_PORT, database=database)


def _ensure_postgres_database():
    """Create DB_NAME automatically if it does not exist yet (visible in pgAdmin afterwards)."""
    admin = create_engine(_pg_url("postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": DB_NAME}).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
                print(f"[db] Created database '{DB_NAME}'")
    except Exception as e:
        raise RuntimeError(
            f"Cannot connect to PostgreSQL at {DB_HOST}:{DB_PORT} as '{DB_USER}'. "
            f"Check that the server is running and your .env values (especially DB_PASSWORD) are correct. "
            f"Original error: {e}") from e
    finally:
        admin.dispose()


if DB_TYPE == "sqlite":
    engine = create_engine("sqlite:///./fx.db", connect_args={"check_same_thread": False})
else:
    _ensure_postgres_database()
    engine = create_engine(_pg_url(DB_NAME), pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


class Rate(Base):
    """One row per currency per day: units of `currency` per 1 USD."""
    __tablename__ = "rates"
    id = Column(Integer, primary_key=True)
    day = Column(Date, index=True, nullable=False)
    currency = Column(String(3), nullable=False)
    per_usd = Column(Float, nullable=False)
    __table_args__ = (UniqueConstraint("day", "currency", name="uq_day_currency"),)


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    pair = Column(String(7), nullable=False)          # e.g. USD/INR
    direction = Column(String(5), nullable=False)     # above | below
    threshold = Column(Float, nullable=False)
    active = Column(Boolean, default=True)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
