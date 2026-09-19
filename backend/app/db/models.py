from datetime import date

from sqlalchemy import JSON, CheckConstraint, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

STATUSES = ("passed", "failed", "skipped")
BUCKETS = ("Actions Required", "Areas of Opportunity", "Strengths", "Not Applicable")
CATEGORIES = ("Security", "Content Modeling", "Content", "Other Configurations")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Stack(Base):
    __tablename__ = "stacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    entries_count: Mapped[int] = mapped_column(Integer)
    assets_count: Mapped[int] = mapped_column(Integer)
    run_date: Mapped[date] = mapped_column(Date)

    results: Mapped[list["CheckResult"]] = relationship(back_populates="stack")


class Check(Base):
    """Static, per-check-type data (the 'light' data)."""

    __tablename__ = "checks"
    __table_args__ = (CheckConstraint(_in("category", CATEGORIES), name="ck_checks_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text)
    recommendation_text: Mapped[str] = mapped_column(Text)

    results: Mapped[list["CheckResult"]] = relationship(back_populates="check")


class CheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = (
        UniqueConstraint("stack_id", "check_id"),
        CheckConstraint(_in("status", STATUSES), name="ck_check_results_status"),
        CheckConstraint(_in("bucket", BUCKETS), name="ck_check_results_bucket"),
        CheckConstraint("entity_count >= 0", name="ck_check_results_entity_count"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stack_id: Mapped[int] = mapped_column(ForeignKey("stacks.id"), index=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("checks.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    bucket: Mapped[str] = mapped_column(String(30))
    entity_count: Mapped[int] = mapped_column(Integer, default=0)

    stack: Mapped[Stack] = relationship(back_populates="results")
    check: Mapped[Check] = relationship(back_populates="results")
    failed_entities: Mapped[list["FailedEntity"]] = relationship(back_populates="result")


class FailedEntity(Base):
    """Per-entity failure detail (the 'heavy' data), fetched on demand."""

    __tablename__ = "failed_entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    check_result_id: Mapped[int] = mapped_column(ForeignKey("check_results.id"), index=True)
    entity_name: Mapped[str] = mapped_column(String(300))
    entity_type: Mapped[str] = mapped_column(String(50))
    extra: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    result: Mapped[CheckResult] = relationship(back_populates="failed_entities")
