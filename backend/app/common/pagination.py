"""Server-side pagination (page/size with total) for enterprise tables."""
from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


def paginate(db: Session, stmt, page: int = 1, size: int = 25, scalars: bool = True):
    page = max(page, 1)
    size = min(max(size, 1), 200)
    total = db.execute(select(func.count()).select_from(stmt.order_by(None).subquery())).scalar_one()
    result = db.execute(stmt.limit(size).offset((page - 1) * size))
    rows = result.scalars().all() if scalars else result.all()
    return rows, total, page, size
