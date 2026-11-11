"""Controlled case state machine (FR-CAS-02, LLD 7). Arbitrary status changes are not possible."""

ACTIVE = ("ASSIGNED", "CONTACT_ATTEMPTED", "CONTACT_ESTABLISHED", "BORROWER_UPDATE_PENDING", "ESCALATED")
OPEN = ("NEW",) + ACTIVE + ("DISPUTED",)
STATUSES = ("NEW",) + ACTIVE + ("DISPUTED", "RESOLVED", "CLOSED")

RESOLUTION_TYPES = {
    "PAYMENT_CONFIRMED": "Bank confirmed payment (bank transaction reference required)",
    "BORROWER_INFORMATION_UPDATED": "Borrower information updated and verified",
    "DATA_CORRECTED": "Data corrected at source",
    "RESTRUCTURE_CONFIRMED_BY_BANK": "Bank confirmed restructuring or deferment",
    "TRANSFERRED": "Transferred to another authorised team",
}

# (from, to): (permission, label, requirement note)
TRANSITIONS: dict[tuple[str, str], tuple[str, str, str | None]] = {
    ("ASSIGNED", "CONTACT_ATTEMPTED"): ("case:update", "Mark contact attempted", None),
    ("ASSIGNED", "CONTACT_ESTABLISHED"): ("case:update", "Mark contact established", None),
    ("CONTACT_ATTEMPTED", "CONTACT_ESTABLISHED"): ("case:update", "Mark contact established", None),
    ("CONTACT_ESTABLISHED", "BORROWER_UPDATE_PENDING"): ("case:update", "Awaiting borrower update", None),
    ("BORROWER_UPDATE_PENDING", "CONTACT_ESTABLISHED"): ("case:update", "Borrower update received", None),
    ("ASSIGNED", "ESCALATED"): ("case:escalate", "Escalate", "At least one recorded follow-up"),
    ("CONTACT_ATTEMPTED", "ESCALATED"): ("case:escalate", "Escalate", "At least one recorded follow-up"),
    ("CONTACT_ESTABLISHED", "ESCALATED"): ("case:escalate", "Escalate", "At least one recorded follow-up"),
    ("BORROWER_UPDATE_PENDING", "ESCALATED"): ("case:escalate", "Escalate", "At least one recorded follow-up"),
    ("ESCALATED", "ASSIGNED"): ("case:escalate", "De-escalate", None),
    ("RESOLVED", "CLOSED"): ("case:close", "Close case", "Reviewer other than the owner for HIGH/CRITICAL"),
    ("RESOLVED", "ASSIGNED"): ("case:close", "Reopen", None),
}
for _s in ACTIVE:
    TRANSITIONS[(_s, "RESOLVED")] = ("case:close", "Resolve", "Resolution type; bank transaction for payment")


REQUIRES = {"ESCALATED": ["note"], "RESOLVED": ["note", "resolution_type"], "CLOSED": ["note"],
            "ASSIGNED": ["note"]}


def allowed(ctx, case, followups: int) -> list[dict]:
    out = []
    for (frm, to), (perm, label, req) in TRANSITIONS.items():
        if frm != case.status:
            continue
        ok = ctx.can(perm) and not (ctx.is_field_officer and to in ("RESOLVED", "CLOSED"))
        reason = None if ok else f"Requires permission {perm}"
        if ok and to == "ESCALATED" and followups == 0:
            ok, reason = False, "Record at least one follow-up before escalating (evidence before escalation)"
        if ok and to == "CLOSED" and case.priority in ("HIGH", "CRITICAL") and case.owner_id == ctx.user_id:
            ok, reason = False, "A different reviewer must close a HIGH or CRITICAL case"
        item = {"to": to, "label": label, "requires": REQUIRES.get(to, []), "permitted": ok,
                "reason_if_blocked": reason, "note": req}
        if to == "RESOLVED":
            item["conditional"] = {"bank_txn_ref": "required when resolution_type is PAYMENT_CONFIRMED"}
        out.append(item)
    return out
