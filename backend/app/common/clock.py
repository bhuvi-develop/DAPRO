"""Business date. Timestamps are stored in UTC (NFR-DAT-02); DPD uses the bank business calendar date."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

BUSINESS_TZ = "Asia/Kolkata"


def business_today(tz: str | None = None) -> date:
    return datetime.now(ZoneInfo(tz or BUSINESS_TZ)).date()
