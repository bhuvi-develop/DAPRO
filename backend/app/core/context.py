"""Per-request context passed to every service method (LLD section 1 coding rules)."""
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import Forbidden


@dataclass
class RequestContext:
    db: Session
    tenant_id: UUID
    user_id: UUID | None
    user_name: str
    org_id: UUID | None
    org_type: str
    org_name: str
    roles: list[str]
    permissions: set[str]
    correlation_id: str
    unit_ids: set[UUID] | None = None  # None = whole organization
    student_id: UUID | None = None  # borrower users
    session_id: UUID | None = None
    ip: str | None = None
    purpose: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def role(self) -> str:
        return self.roles[0] if self.roles else "NONE"

    @property
    def is_bank(self) -> bool:
        return self.org_type in ("BANK", "NBFC", "AGENCY")

    @property
    def is_college(self) -> bool:
        return self.org_type == "COLLEGE"

    @property
    def is_borrower(self) -> bool:
        return "BORROWER" in self.roles

    @property
    def is_field_officer(self) -> bool:
        return self.roles == ["FIELD_OFFICER"]

    def can(self, permission: str) -> bool:
        return permission in self.permissions

    def require(self, permission: str, what: str | None = None) -> None:
        if permission not in self.permissions:
            raise Forbidden(f"Your role does not allow {what or permission}.")

    def audit(self, action: str, *, target_type: str | None = None, target_id=None, target_label: str | None = None,
              outcome: str = "SUCCESS", payload: dict | None = None, purpose: str | None = None):
        return audit.write(self.db, tenant_id=self.tenant_id, action=action, outcome=outcome, actor_id=self.user_id,
                           actor_label=self.user_name, actor_role=self.role, org_id=self.org_id,
                           target_type=target_type, target_id=target_id, target_label=target_label,
                           purpose=purpose or self.purpose, correlation_id=self.correlation_id, ip=self.ip,
                           payload=payload)

    def commit(self) -> None:
        self.db.commit()
