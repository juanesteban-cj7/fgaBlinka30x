import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

if TYPE_CHECKING:
    from app.models.app_user import AppUser

POLICY_CREATED = "POLICY_CREATED"
POLICY_ACTIVATED = "POLICY_ACTIVATED"
POLICY_BUDGET_UPDATED = "POLICY_BUDGET_UPDATED"
BENEFICIARY_CREATED = "BENEFICIARY_CREATED"
BENEFICIARY_UPDATED = "BENEFICIARY_UPDATED"
BENEFICIARY_DELETED = "BENEFICIARY_DELETED"
INVOICE_UPLOADED = "INVOICE_UPLOADED"
INVOICE_APPROVED = "INVOICE_APPROVED"
INVOICE_REJECTED = "INVOICE_REJECTED"
INVOICE_EVALUATED = "INVOICE_EVALUATED"


def record_audit(
    db: Session,
    *,
    actor: "AppUser | None",
    action: str,
    entity_type: str,
    entity_id: str,
    entity_label: str,
    summary: str,
    changes: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    company_id: str | None = None,
) -> AuditLog:
    actor_type = "user" if actor else "system"
    entry = AuditLog(
        id=str(uuid.uuid4()),
        actor_type=actor_type,
        actor_id=actor.id if actor else None,
        actor_name=actor.full_name if actor else "Sistema",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        company_id=company_id,
        summary=summary,
        changes=changes,
        event_metadata=metadata,
    )
    db.add(entry)
    return entry
