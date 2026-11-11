"""Versioned, effective-dated policy configuration lookup (BR-02, BR-12, FR-ADM-01)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

DEFAULTS: dict[str, dict] = {
    "DPD_BUCKETS": {"buckets": [
        {"code": "CURRENT", "label": "Current / upcoming", "min": 0, "max": 0},
        {"code": "DPD_1_30", "label": "Early overdue", "min": 1, "max": 30},
        {"code": "DPD_31_60", "label": "Overdue review", "min": 31, "max": 60},
        {"code": "DPD_61_90", "label": "Priority review", "min": 61, "max": 90},
        {"code": "DPD_90_PLUS", "label": "Critical review", "min": 91, "max": None}]},
    "REPAYMENT_RULES": {"grace_days": 0, "partial_payment_satisfies": False, "allocation": "BANK_SUPPLIED",
                        "business_timezone": "Asia/Kolkata"},
    "DATA_FRESHNESS": {"stale_after_hours": 48},
    "GRIEVANCE_SLA": {"days": 15},
    "COMMUNICATION_WINDOW": {"quiet_start": "21:00", "quiet_end": "08:00", "max_per_week": 3},
    "CASE_DEFAULTS": {"due_days": {"CRITICAL": 2, "HIGH": 5, "MEDIUM": 10, "LOW": 20}},
    "MAKER_CHECKER": {"bank_import_approval": True, "guarantor_change_approval": True, "risk_rule_approval": True},
}


def get_policy(db: Session, key: str, on: date | None = None) -> dict:
    from app.models.platform import PolicyConfig

    on = on or date.today()
    row = db.execute(select(PolicyConfig).where(PolicyConfig.key == key, PolicyConfig.status == "ACTIVE",
                                                PolicyConfig.effective_from <= on)
                     .order_by(PolicyConfig.version.desc()).limit(1)).scalar()
    if row is None:
        return {"key": key, "version": 0, "approval_label": "NOT_CONFIGURED", "value": DEFAULTS.get(key, {})}
    return {"key": key, "version": row.version, "approval_label": row.approval_label, "value": row.value}
