"""Decision log / case-management store (SQLite by default, PostgreSQL-ready).

Every decision is stored with the model version, the exact feature vector and
the explanation: a forensic audit trail. Any past verdict can be
reproduced and justified in a dispute, and analysts' feedback is kept as
labels for future retraining.

Set ``FRAUDLENS_DB_URL`` (e.g. ``postgresql+psycopg://user:pw@host/db``) to
use PostgreSQL instead of the local SQLite file.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .. import config

DB_URL = os.getenv("FRAUDLENS_DB_URL", f"sqlite:///{(config.ARTIFACTS / 'fraudlens.db').as_posix()}")


class Base(DeclarativeBase):
    pass


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    source: Mapped[str] = mapped_column(String(16))                 # stream | manual | scenario
    card_token: Mapped[str] = mapped_column(String(16), index=True)
    card_last4: Mapped[str] = mapped_column(String(4))
    txn_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(32))
    merchant: Mapped[str] = mapped_column(String(128))
    probability: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(8), index=True)
    decision: Mapped[str] = mapped_column(String(8))
    p_xgb: Mapped[float] = mapped_column(Float)
    p_rf: Mapped[float] = mapped_column(Float)
    anomaly_pct: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    mitigating: Mapped[list] = mapped_column(JSON, default=list)
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    policy: Mapped[list] = mapped_column(JSON, default=list)                  # policy rules / novelty alarm that fired
    model_version: Mapped[str] = mapped_column(String(32))
    latency_ms: Mapped[float] = mapped_column(Float)
    label: Mapped[int | None] = mapped_column(Integer, nullable=True)        # dataset ground truth (replay only)
    review_status: Mapped[str] = mapped_column(String(12), default="n/a")    # open | confirmed | dismissed | n/a
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})


def init_db(reset: bool = False) -> None:
    """Create the decision log. ``reset`` (used when a demo session restarts)
    rebuilds the table, so an old database file never lags behind the schema."""
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
