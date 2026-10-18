from datetime import datetime

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


def test_audit_log_filters_and_paginates(client, db_session, test_user):
    rows = [
        AuditLog(
            id="audit_page_1",
            created_at=datetime(2026, 1, 2, 9),
            actor_type="user",
            actor_id=test_user.id,
            actor_name="Ana Pérez",
            action="INVOICE_APPROVED",
            entity_type="invoice",
            entity_id="inv_a",
            entity_label="A001",
            summary="Ana Pérez aprobó la factura A001",
            event_metadata={"reason": "Revisada"},
        ),
        AuditLog(
            id="audit_page_2",
            created_at=datetime(2026, 1, 2, 10),
            actor_type="user",
            actor_id=test_user.id,
            actor_name="Ana Pérez",
            action="INVOICE_REJECTED",
            entity_type="invoice",
            entity_id="inv_b",
            entity_label="A002",
            summary="Ana Pérez rechazó la factura A002",
        ),
        AuditLog(
            id="audit_page_3",
            created_at=datetime(2026, 1, 3, 10),
            actor_type="user",
            actor_id="otro_usuario",
            actor_name="Carlos Ruiz",
            action="INVOICE_APPROVED",
            entity_type="invoice",
            entity_id="inv_c",
            entity_label="A003",
            summary="Carlos Ruiz aprobó la factura A003",
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()

    response = client.get(
        "/api/v1/audit-log",
        params=[
            ("action", "INVOICE_APPROVED"),
            ("action", "INVOICE_REJECTED"),
            ("entity_type", "invoice"),
            ("actor_id", test_user.id),
            ("date_from", "2026-01-02"),
            ("date_to", "2026-01-02"),
            ("q", "ana"),
            ("limit", "1"),
            ("offset", "0"),
        ],
    )
    assert response.status_code == 200, response.text
    page = response.json()
    assert page["total"] == 2
    assert len(page["items"]) == 1
    assert page["items"][0]["id"] == "audit_page_2"
    assert page["items"][0]["metadata"] is None

    next_page = client.get(
        "/api/v1/audit-log",
        params={
            "action": "INVOICE_APPROVED",
            "entity_type": "invoice",
            "actor_id": test_user.id,
            "date_from": "2026-01-02",
            "date_to": "2026-01-02",
            "q": "aprobó",
            "limit": 5,
        },
    )
    assert next_page.status_code == 200, next_page.text
    assert next_page.json()["items"][0]["metadata"] == {"reason": "Revisada"}


def test_audit_log_has_no_mutation_routes(client, unauthenticated_client):
    assert client.patch("/api/v1/audit-log").status_code == 405
    assert client.delete("/api/v1/audit-log").status_code == 405
    assert unauthenticated_client.get("/api/v1/audit-log").status_code == 200


def test_audit_log_accepts_both_trailing_slash_forms(client):
    for path in ("/api/v1/audit-log", "/api/v1/audit-log/"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 200, (path, response.text)
