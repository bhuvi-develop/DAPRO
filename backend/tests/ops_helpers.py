"""Shared helpers for operations-module tests (risk, cases, field, comms, grievances, portal)."""
from sqlalchemy import text


def uid(db, email):
    return str(db.execute(text("select id from users where email = :e"), {"e": email}).scalar())


def borrowers(db) -> list[tuple[str, str]]:
    rows = db.execute(text(
        "select u.email, u.student_id from users u join user_roles ur on ur.user_id = u.id "
        "join roles r on r.id = ur.role_id where r.code = :r and u.status = :s order by u.email"),
        {"r": "BORROWER", "s": "ACTIVE"}).all()
    return [(r[0], str(r[1])) for r in rows]


def never_quiet(db, student_id):
    db.execute(text("update contact_preferences set quiet_start = :t, quiet_end = :t, allowed = true "
                    "where student_id = :s"), {"t": "00:00", "s": student_id})
    db.commit()


def anb_student_with_loan(db, status="OVERDUE", offset=0):
    return db.execute(text(
        "select l.student_id, l.id from loan_accounts l join organizations o on o.id = l.bank_org_id "
        "where o.code = :b and l.repayment_status = :st and l.link_status = :ls order by l.bank_loan_ref "
        "offset :o limit 1"), {"b": "ANB", "st": status, "ls": "LINKED", "o": offset}).one()
