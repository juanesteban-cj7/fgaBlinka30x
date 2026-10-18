from app.models.audit_log import AuditLog
from app.services.audit import record_audit


def test_record_audit_adds_append_only_snapshot_without_commit(db_session, test_user):
    entry = record_audit(
        db_session,
        actor=test_user,
        action="BENEFICIARY_CREATED",
        entity_type="beneficiary",
        entity_id="ben_audit_test",
        entity_label="Proveedor Demo",
        summary=f"{test_user.full_name} añadió al beneficiario Proveedor Demo",
        changes={"name": {"before": None, "after": "Proveedor Demo"}},
        metadata={"source": "test"},
        company_id="co_demo_001",
    )

    assert entry in db_session
    assert entry.actor_type == "user"
    assert entry.actor_id == test_user.id
    assert entry.actor_name == test_user.full_name
    assert entry.changes["name"]["after"] == "Proveedor Demo"
    assert entry.event_metadata == {"source": "test"}

    db_session.rollback()
    assert db_session.query(AuditLog).filter_by(id=entry.id).first() is None


def test_record_system_audit_uses_system_snapshot(db_session):
    entry = record_audit(
        db_session,
        actor=None,
        action="INVOICE_EVALUATED",
        entity_type="invoice",
        entity_id="inv_audit_test",
        entity_label="T-001",
        summary="Sistema evaluó la factura T-001",
    )

    assert entry.actor_type == "system"
    assert entry.actor_id is None
    assert entry.actor_name == "Sistema"
