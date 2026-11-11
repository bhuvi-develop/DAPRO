"""Field masking for personal and financial data (FR-STU-07, NFR-PRV-02)."""
from decimal import Decimal

from app.core.context import RequestContext


def mask_mobile(v: str | None) -> str | None:
    if not v:
        return v
    digits = v.replace(" ", "")
    return digits[:3] + "*" * max(len(digits) - 6, 0) + digits[-3:] if len(digits) > 6 else "***"


def mask_email(v: str | None) -> str | None:
    if not v or "@" not in v:
        return v
    name, dom = v.split("@", 1)
    return (name[:2] + "***@" + dom) if len(name) > 2 else ("***@" + dom)


def contact(ctx: RequestContext, kind: str, v: str | None) -> str | None:
    if ctx.can("student:pii_full") or ctx.is_borrower:
        return v
    return mask_email(v) if kind == "EMAIL" else mask_mobile(v)


def money(ctx: RequestContext, v: Decimal | None) -> str | None:
    """Bank-sourced amounts are returned only to roles holding loan:financial (AC-02 / college restriction)."""
    if v is None or not (ctx.can("loan:financial") or ctx.is_borrower):
        return None
    return f"{v:.2f}"


def financial_visible(ctx: RequestContext) -> bool:
    return ctx.can("loan:financial") or ctx.is_borrower
