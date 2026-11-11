"""Declarative base, common column helpers and mixins."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.ids import uuid7

Money = Numeric(18, 2)


class Base(DeclarativeBase):
    type_annotation_map = {
        uuid.UUID: UUID(as_uuid=True),
        datetime: DateTime(timezone=True),
        date: Date,
        Decimal: Money,
        dict: JSONB,
        list: JSONB,
        str: Text,
    }


def pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)


def fk(target: str, nullable: bool = False, index: bool = True, ondelete: str | None = None):
    return mapped_column(UUID(as_uuid=True), ForeignKey(target, ondelete=ondelete), nullable=nullable, index=index)


def created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def updated() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


def scol(length: int = 40, nullable: bool = False, default: str | None = None, index: bool = False):
    return mapped_column(String(length), nullable=nullable, default=default, server_default=default,
                         index=index)


def text_array():
    return mapped_column(ARRAY(Text), nullable=False, default=list, server_default="{}")


class TenantMixin:
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True,
                                                 nullable=False)


# Tables protected by PostgreSQL row-level security (tenant isolation).
RLS_TABLES: list[str] = []


def rls(cls):
    RLS_TABLES.append(cls.__tablename__)
    return cls
