"""Initial explainable rule catalogue (RD section 10.3, UC-12, UC-13).

These are DEMO_FIXTURE definitions: categories, thresholds and severities require bank approval (OD-15,
FR-RSK-04). Rules prioritise human review; they never label a borrower as absconding, fraudulent or
unwilling to repay (FR-RSK-07, BR-05, BR-06), and never trigger legal or adverse action (FR-RSK-08).
"""

CATEGORIES = {
    "FINANCIAL_DELINQUENCY": "Financial delinquency (bank-confirmed)",
    "CONTACT_DATA_QUALITY": "Contact and address data quality",
    "DATA_SYNCHRONIZATION": "Data synchronization",
    "OPERATIONAL_FOLLOW_UP": "Operational follow-up",
}

RULES: list[dict] = [
    {"code": "REPAYMENT_OVERDUE", "name": "Repayment overdue (bank-confirmed)", "category": "FINANCIAL_DELINQUENCY",
     "severity": "MEDIUM", "params": {"min_dpd": 1, "high_dpd": 61},
     "description": "Bank-confirmed instalment remains unpaid beyond the approved threshold. Only evaluated when bank data is CURRENT.",
     "recommended_action": "Open a repayment follow-up review. Confirm the amount with bank data before any contact."},
    {"code": "REPEATED_OVERDUE", "name": "Repeated overdue instalments", "category": "FINANCIAL_DELINQUENCY",
     "severity": "HIGH", "params": {"min_overdue_instalments": 3},
     "description": "Configured number of overdue or partially paid instalments confirmed by the bank.",
     "recommended_action": "Increase review priority. Human approval is required before any escalation."},
    {"code": "DATA_STALE", "name": "Bank data stale or unavailable", "category": "DATA_SYNCHRONIZATION",
     "severity": "LOW", "params": {},
     "description": "Bank synchronization is older than the agreed interval or failed. This is a data-quality alert only.",
     "recommended_action": "Raise a data-quality alert with the bank integration owner. Do not infer default."},
    {"code": "ADDRESS_UPDATE_NEEDED", "name": "Address update or verification needed", "category": "CONTACT_DATA_QUALITY",
     "severity": "LOW", "params": {},
     "description": "Current address verification FAILED or DISPUTED, or a graduate has no verified current address.",
     "recommended_action": "Create an address maintenance task and request a borrower update through approved channels."},
    {"code": "CONTACT_UNSUCCESSFUL", "name": "Documented contact attempts unsuccessful", "category": "OPERATIONAL_FOLLOW_UP",
     "severity": "MEDIUM", "params": {"min_attempts": 3, "window_days": 30},
     "description": "Configured number of documented, compliant contact attempts without contact in the window.",
     "recommended_action": "Manager review. This is not evidence of absconding (BR-05)."},
    {"code": "EMPLOYMENT_UPDATE_DUE", "name": "Post-study update due", "category": "OPERATIONAL_FOLLOW_UP",
     "severity": "LOW", "params": {"days_after_graduation": 180},
     "description": "Graduate has no post-study status recorded within the approved window.",
     "recommended_action": "Send a neutral update request if communication preferences allow."},
    {"code": "MORATORIUM_ENDING", "name": "Moratorium ending - engage before first EMI", "category": "OPERATIONAL_FOLLOW_UP",
     "severity": "LOW", "params": {"days_before": 45},
     "description": "Moratorium ends within the window. Engage the student before the first instalment is due (UC-13).",
     "recommended_action": "Confirm contact details and repayment readiness. Route further-study cases to bank deferment policy."},
    {"code": "DISPUTED_RECORD", "name": "Disputed record", "category": "OPERATIONAL_FOLLOW_UP",
     "severity": "REVIEW_REQUIRED", "params": {},
     "description": "Borrower has an open dispute about identity, address, amount or contact.",
     "recommended_action": "Pause affected outreach and route to the grievance owner."},
]

SEVERITIES = ["LOW", "MEDIUM", "HIGH", "REVIEW_REQUIRED"]
