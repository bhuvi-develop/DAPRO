"""Organizations, units and data-sharing agreements (FR-ORG-01..04)."""
from sqlalchemy import func, or_, select

from app.core.context import RequestContext
from app.core.errors import BusinessError, Forbidden, NotFound, ValidationFailed
from app.models.iam import Organization, OrgUnit, SharingAgreement, User


def org_dict(o: Organization, users: int | None = None, units: int | None = None) -> dict:
    return {"id": str(o.id), "type": o.type, "code": o.code, "name": o.name, "legal_name": o.legal_name,
            "status": o.status, "city": o.city, "state": o.state, "contact_email": o.contact_email,
            "user_count": users, "unit_count": units, "created_at": o.created_at}


def list_orgs(ctx: RequestContext, type_: str | None = None) -> list[dict]:
    stmt = select(Organization).where(Organization.tenant_id == ctx.tenant_id)
    if type_:
        stmt = stmt.where(Organization.type == type_)
    users = dict(ctx.db.execute(select(User.org_id, func.count()).where(User.tenant_id == ctx.tenant_id)
                                .group_by(User.org_id)).all())
    units = dict(ctx.db.execute(select(OrgUnit.org_id, func.count()).where(OrgUnit.tenant_id == ctx.tenant_id)
                                .group_by(OrgUnit.org_id)).all())
    show = ctx.can("user:read")
    rows = ctx.db.execute(stmt.order_by(Organization.type, Organization.name)).scalars()
    return [org_dict(o, users.get(o.id, 0) if show else None, units.get(o.id, 0)) for o in rows]


def get_org(ctx, org_id) -> Organization:
    try:
        o = ctx.db.get(Organization, org_id)
    except Exception:
        o = None
    if o is None or o.tenant_id != ctx.tenant_id:
        raise NotFound("Organization")
    return o


def create_org(ctx: RequestContext, body) -> dict:
    dup = ctx.db.execute(select(Organization.id).where(Organization.tenant_id == ctx.tenant_id,
                                                       Organization.code == body.code)).scalar()
    if dup:
        raise BusinessError("DUPLICATE_CODE", "An organization with this code already exists.", "Use a unique code.")
    o = Organization(tenant_id=ctx.tenant_id, **body.model_dump(exclude_none=True))
    ctx.db.add(o)
    ctx.db.flush()
    ctx.audit("org.created", target_type="organization", target_id=o.id, target_label=o.name,
              payload={"type": o.type, "code": o.code})
    ctx.commit()
    return org_dict(o, 0, 0)


def update_org(ctx: RequestContext, org_id, body) -> dict:
    o = get_org(ctx, org_id)
    if o.type == "PLATFORM" and body.status and body.status != "ACTIVE":
        raise BusinessError("NOT_ALLOWED", "The platform organization cannot be suspended.", None)
    changes = body.model_dump(exclude_none=True)
    for k, v in changes.items():
        setattr(o, k, v)
    ctx.audit("org.updated", target_type="organization", target_id=o.id, target_label=o.name,
              payload={"fields": sorted(changes)})
    ctx.commit()
    return org_dict(o)


def unit_dict(u: OrgUnit) -> dict:
    return {"id": str(u.id), "org_id": str(u.org_id), "parent_id": str(u.parent_id) if u.parent_id else None,
            "kind": u.kind, "code": u.code, "name": u.name, "city": u.city, "state": u.state, "status": u.status}


def list_units(ctx: RequestContext, org_id: str | None) -> list[dict]:
    stmt = select(OrgUnit).where(OrgUnit.tenant_id == ctx.tenant_id)
    if org_id:
        stmt = stmt.where(OrgUnit.org_id == org_id)
    return [unit_dict(u) for u in ctx.db.execute(stmt.order_by(OrgUnit.kind, OrgUnit.name)).scalars()]


def create_unit(ctx: RequestContext, body) -> dict:
    o = get_org(ctx, body.org_id)
    if not ctx.can("org:manage") and o.id != ctx.org_id:
        raise Forbidden("You can only add units to your own organization.")
    if body.parent_id:
        p = ctx.db.get(OrgUnit, body.parent_id)
        if p is None or p.org_id != o.id:
            raise ValidationFailed("Parent unit must belong to the same organization.")
    if ctx.db.execute(select(OrgUnit.id).where(OrgUnit.org_id == o.id, OrgUnit.code == body.code)).scalar():
        raise BusinessError("DUPLICATE_CODE", "A unit with this code already exists.", "Use a unique code.")
    u = OrgUnit(tenant_id=ctx.tenant_id, **body.model_dump(exclude_none=True))
    ctx.db.add(u)
    ctx.db.flush()
    ctx.audit("org_unit.created", target_type="org_unit", target_id=u.id, target_label=u.name,
              payload={"org": o.code, "kind": u.kind})
    ctx.commit()
    return unit_dict(u)


def agreement_dict(a: SharingAgreement, names: dict) -> dict:
    return {"id": str(a.id), "reference": a.reference, "college_org_id": str(a.college_org_id),
            "college_name": names.get(a.college_org_id), "bank_org_id": str(a.bank_org_id),
            "bank_name": names.get(a.bank_org_id), "purposes": a.purposes, "shared_fields": a.shared_fields,
            "status": a.status, "effective_from": a.effective_from, "effective_to": a.effective_to,
            "approval_label": a.approval_label, "notes": a.notes}


def list_agreements(ctx: RequestContext) -> list[dict]:
    stmt = select(SharingAgreement)
    if ctx.org_type != "PLATFORM":
        stmt = stmt.where(or_(SharingAgreement.college_org_id == ctx.org_id,
                              SharingAgreement.bank_org_id == ctx.org_id))
    names = {o.id: o.name for o in ctx.db.execute(select(Organization)).scalars()}
    return [agreement_dict(a, names) for a in ctx.db.execute(stmt.order_by(SharingAgreement.reference)).scalars()]


def create_agreement(ctx: RequestContext, body) -> dict:
    c, b = get_org(ctx, body.college_org_id), get_org(ctx, body.bank_org_id)
    if c.type != "COLLEGE" or b.type not in ("BANK", "NBFC"):
        raise ValidationFailed("An agreement links one college and one bank or NBFC.")
    a = SharingAgreement(tenant_id=ctx.tenant_id, reference=body.reference, college_org_id=c.id, bank_org_id=b.id,
                         purposes=body.purposes, shared_fields=body.shared_fields, status="PENDING",
                         effective_from=body.effective_from, effective_to=body.effective_to,
                         approval_label="PENDING_LEGAL_APPROVAL", notes=body.notes)
    ctx.db.add(a)
    ctx.db.flush()
    ctx.audit("sharing_agreement.created", target_type="sharing_agreement", target_id=a.id, target_label=a.reference)
    ctx.commit()
    return agreement_dict(a, {c.id: c.name, b.id: b.name})
