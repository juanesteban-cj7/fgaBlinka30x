def test_list_empty_beneficiaries(client):
    response = client.get("/api/v1/beneficiaries")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_beneficiary(client, db_session):
    payload = {
        "id": "ben_test_01",
        "company_id": "co_demo_001",
        "name": "Beneficiario Prueba S.A.S.",
        "normalized_name": "beneficiario prueba sas",
        "allowed": True,
        "reference_code": "BTP-01",
        "category": "Pruebas",
    }
    response = client.post("/api/v1/beneficiaries", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "ben_test_01"
    assert data["allowed"] is True

    response = client.get("/api/v1/beneficiaries?company_id=co_demo_001")
    assert response.status_code == 200
    assert len(response.json()) == 1
    from app.models.audit_log import AuditLog

    event = db_session.query(AuditLog).filter_by(
        action="BENEFICIARY_CREATED", entity_id="ben_test_01"
    ).one()
    assert event.actor_id == "demo_user"
    assert event.actor_name == "Usuario de demostración"
    assert event.entity_label == "Beneficiario Prueba S.A.S."


def test_action_and_audit_are_atomic_when_commit_fails(client, db_session, monkeypatch):
    import pytest
    from sqlalchemy.orm import Session

    from app.models.audit_log import AuditLog
    from app.models.beneficiary import Beneficiary
    from app.models.company import CompanyDemo

    db_session.add(CompanyDemo(id="co_atomicity", name="Empresa", currency_base="USD"))
    db_session.commit()

    def fail_commit(_session):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(Session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="simulated commit failure"):
        client.post(
            "/api/v1/beneficiaries",
            json={
                "id": "ben_atomicity",
                "company_id": "co_atomicity",
                "name": "Proveedor",
            },
        )

    assert db_session.query(Beneficiary).filter_by(id="ben_atomicity").count() == 0
    assert db_session.query(AuditLog).filter_by(entity_id="ben_atomicity").count() == 0


def test_create_beneficiary_normalizes_name_on_server(client):
    response = client.post(
        "/api/v1/beneficiaries",
        json={
            "id": "ben_normalized_01",
            "company_id": "co_demo_001",
            "name": "  Proveedor Pacífico S.A.S. ",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["normalized_name"] == "proveedor pacifico sas"


def test_create_duplicate_beneficiary_fails(client):
    payload = {
        "id": "ben_test_02",
        "company_id": "co_demo_001",
        "name": "Dup S.A.S.",
        "normalized_name": "dup sas",
    }
    client.post("/api/v1/beneficiaries", json=payload)
    response = client.post("/api/v1/beneficiaries", json=payload)
    assert response.status_code == 400


def test_update_beneficiary_updates_name_and_normalized_name(client, db_session):
    payload = {
        "id": "ben_update_01",
        "company_id": "co_demo_001",
        "name": "Proveedor Original",
        "normalized_name": "proveedor original",
    }
    created = client.post("/api/v1/beneficiaries", json=payload)
    assert created.status_code == 201

    response = client.patch(
        "/api/v1/beneficiaries/ben_update_01",
        json={"name": "  Proveedor Pacífico S.A.S.  ", "category": "Servicios"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Proveedor Pacífico S.A.S."
    assert response.json()["normalized_name"] == "proveedor pacifico sas"
    assert response.json()["category"] == "Servicios"
    from app.models.audit_log import AuditLog

    event = db_session.query(AuditLog).filter_by(
        action="BENEFICIARY_UPDATED", entity_id="ben_update_01"
    ).one()
    assert event.changes["name"] == {
        "before": "Proveedor Original",
        "after": "Proveedor Pacífico S.A.S.",
    }
    assert event.actor_id == "demo_user"


def test_update_missing_beneficiary_returns_not_found(client, db_session):
    response = client.patch(
        "/api/v1/beneficiaries/no-existe",
        json={"name": "Proveedor"},
    )

    assert response.status_code == 404


def test_beneficiary_patch_without_changes_does_not_add_audit_event(client, db_session):
    from app.models.audit_log import AuditLog
    from app.models.beneficiary import Beneficiary
    from app.models.company import CompanyDemo

    db_session.add(CompanyDemo(id="co_patch_noop", name="Empresa", currency_base="USD"))
    db_session.add(Beneficiary(
        id="ben_patch_noop", company_id="co_patch_noop", name="Proveedor",
        normalized_name="proveedor", allowed=True,
    ))
    db_session.commit()

    response = client.patch("/api/v1/beneficiaries/ben_patch_noop", json={"name": "Proveedor"})

    assert response.status_code == 200, response.text
    assert db_session.query(AuditLog).filter_by(
        entity_id="ben_patch_noop", action="BENEFICIARY_UPDATED"
    ).count() == 0


def test_delete_unreferenced_beneficiary(client, db_session):
    from app.models.beneficiary import Beneficiary
    from app.models.company import CompanyDemo

    db_session.add(CompanyDemo(id="co_delete", name="Empresa", currency_base="USD"))
    db_session.add(Beneficiary(
        id="ben_delete", company_id="co_delete", name="Proveedor",
        normalized_name="proveedor", allowed=True,
    ))
    db_session.commit()

    response = client.delete("/api/v1/beneficiaries/ben_delete")

    assert response.status_code == 204
    assert db_session.query(Beneficiary).filter_by(id="ben_delete").first() is None
    from app.models.audit_log import AuditLog

    event = db_session.query(AuditLog).filter_by(
        action="BENEFICIARY_DELETED", entity_id="ben_delete"
    ).one()
    assert event.entity_label == "Proveedor"
    assert event.event_metadata["snapshot"]["name"] == "Proveedor"


def test_delete_beneficiary_with_invoice_returns_conflict(client, db_session):
    from app.models.beneficiary import Beneficiary
    from app.models.company import CompanyDemo
    from app.models.invoice import Invoice

    db_session.add(CompanyDemo(id="co_delete_invoice", name="Empresa", currency_base="USD"))
    db_session.add(Beneficiary(
        id="ben_delete_invoice", company_id="co_delete_invoice", name="Proveedor",
        normalized_name="proveedor", allowed=True,
    ))
    db_session.add(Invoice(
        id="inv_delete_ref", company_id="co_delete_invoice",
        beneficiary_id="ben_delete_invoice", source_type="manual", status="PENDING",
    ))
    db_session.commit()

    response = client.delete("/api/v1/beneficiaries/ben_delete_invoice")

    assert response.status_code == 409
    assert "facturas o acuerdos asociados" in response.json()["detail"]


def test_delete_beneficiary_with_agreement_returns_conflict(client, db_session):
    from datetime import date

    from app.models.agreement import Agreement
    from app.models.beneficiary import Beneficiary
    from app.models.company import CompanyDemo

    db_session.add(CompanyDemo(id="co_delete_agreement", name="Empresa", currency_base="USD"))
    db_session.add(Beneficiary(
        id="ben_delete_agreement", company_id="co_delete_agreement", name="Proveedor",
        normalized_name="proveedor", allowed=True,
    ))
    db_session.add(Agreement(
        id="agr_delete_ref", company_id="co_delete_agreement",
        beneficiary_id="ben_delete_agreement", description="Servicio",
        expected_amount=100, currency="USD", valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
    ))
    db_session.commit()

    response = client.delete("/api/v1/beneficiaries/ben_delete_agreement")

    assert response.status_code == 409
    assert "facturas o acuerdos asociados" in response.json()["detail"]


def test_create_policy(client, db_session):
    from app.models.company import CompanyDemo
    from app.models.policy_change_reason import PolicyChangeReason
    from app.rules.catalog import RULE_CATALOG

    db_session.add(CompanyDemo(id="co_demo_001", name="Co Demo", currency_base="USD"))
    db_session.commit()

    payload = {
        "company_id": "co_demo_001",
        "version": 1,
        "activate": True,
        "change_reason": "Versión inicial para pruebas",
        "currency": "USD",
        "max_invoice_amount": "5000.00",
        "approval_threshold": "1000.00",
        "period_budget": "12000.00",
        "period_type": "monthly",
        "period_basis": "issue_date",
        "rule_actions": [{"code": item["code"], "action": item["default_action"]} for item in RULE_CATALOG],
    }
    response = client.put("/api/v1/policy", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "pol_co_demo_001_v1"
    assert data["version"] == 1
    assert data["active"] is True
    policy_id = data["id"]

    response = client.post("/api/v1/policy/activate", json={"policy_id": policy_id})
    assert response.status_code == 200
    assert response.json() == {"policy_id": policy_id, "active": True}

    response = client.get("/api/v1/policy")
    assert response.status_code == 200
    assert response.json()["id"] == policy_id

    second_payload = {**payload, "version": 2, "activate": False, "change_reason": "Ajuste de política"}
    response = client.put("/api/v1/policy", json=second_payload)
    assert response.status_code == 200
    second_policy_id = response.json()["id"]
    assert response.json()["active"] is False
    assert client.get("/api/v1/policy").json()["id"] == policy_id

    response = client.post("/api/v1/policy/activate", json={"policy_id": second_policy_id})
    assert response.status_code == 200
    assert client.get("/api/v1/policy").json()["id"] == second_policy_id

    response = client.get("/api/v1/policy/versions")
    assert response.status_code == 200
    assert [version["version"] for version in response.json()] == [2, 1]
    reasons = {
        entry.policy_id: entry.reason
        for entry in db_session.query(PolicyChangeReason).all()
    }
    assert reasons == {
        policy_id: "Versión inicial para pruebas",
        second_policy_id: "Ajuste de política",
    }


def test_policy_contract_rejects_blank_change_reason(client):
    from app.rules.catalog import RULE_CATALOG

    payload = {
        "company_id": "co_demo_001",
        "version": 1,
        "currency": "USD",
        "max_invoice_amount": 5000,
        "approval_threshold": 1000,
        "period_budget": 12000,
        "period_type": "monthly",
        "period_basis": "issue_date",
        "rule_actions": [{"code": item["code"], "action": item["default_action"]} for item in RULE_CATALOG],
        "change_reason": "   ",
        "activate": True,
    }
    response = client.put("/api/v1/policy", json=payload)
    assert response.status_code == 422
    assert any("change_reason" in ".".join(map(str, issue["loc"])) for issue in response.json()["detail"])


def test_policy_audit_diff_activation_and_budget(client, db_session):
    from app.models.audit_log import AuditLog
    from app.models.company import CompanyDemo
    from app.rules.catalog import RULE_CATALOG

    db_session.add(CompanyDemo(id="co_audit_policy", name="Empresa", currency_base="USD"))
    db_session.commit()
    payload = {
        "company_id": "co_audit_policy",
        "version": 1,
        "currency": "USD",
        "max_invoice_amount": "5000",
        "approval_threshold": "1000",
        "period_budget": "4000",
        "period_type": "monthly",
        "period_basis": "issue_date",
        "amount_tolerance_pct": "0",
        "min_extraction_confidence": 0.8,
        "name_similarity_threshold": 0.85,
        "possible_duplicate_date_window_days": 0,
        "rule_actions": [
            {"code": item["code"], "action": item["default_action"]}
            for item in RULE_CATALOG
        ],
        "change_reason": "Versión inicial de prueba",
        "activate": True,
    }

    first = client.put("/api/v1/policy/", json=payload)
    assert first.status_code == 200, first.text
    first_id = first.json()["id"]
    first_events = db_session.query(AuditLog).filter_by(entity_id=first_id).all()
    assert [event.action for event in first_events].count("POLICY_CREATED") == 1
    assert [event.action for event in first_events].count("POLICY_ACTIVATED") == 1
    created_event = next(event for event in first_events if event.action == "POLICY_CREATED")
    assert created_event.actor_id == "demo_user"
    assert created_event.event_metadata["change_reason"] == "Versión inicial de prueba"

    second = client.put(
        "/api/v1/policy/",
        json={
            **payload,
            "version": 2,
            "period_budget": "4500",
            "rule_actions": [
                {
                    "code": action["code"],
                    "action": (
                        "BLOCKED"
                        if action["code"] == "MISSING_REQUIRED_FIELDS"
                        else action["action"]
                    ),
                }
                for action in payload["rule_actions"]
            ],
            "activate": False,
            "change_reason": "Aumento de presupuesto",
        },
    )
    assert second.status_code == 200, second.text
    second_id = second.json()["id"]
    second_event = db_session.query(AuditLog).filter_by(
        action="POLICY_CREATED", entity_id=second_id
    ).one()
    assert second_event.changes["period_budget"] == {"before": "4000", "after": "4500"}
    assert second_event.changes["rule_actions"] == {
        "before": {**{item["code"]: item["action"] for item in payload["rule_actions"]},
                   "MISSING_REQUIRED_FIELDS": "NEEDS_HUMAN_APPROVAL"},
        "after": {**{item["code"]: item["action"] for item in payload["rule_actions"]},
                  "MISSING_REQUIRED_FIELDS": "BLOCKED"},
    }
    assert second_event.event_metadata["change_reason"] == "Aumento de presupuesto"

    activated = client.post("/api/v1/policy/activate", json={"policy_id": second_id})
    assert activated.status_code == 200, activated.text
    activation = db_session.query(AuditLog).filter_by(
        action="POLICY_ACTIVATED", entity_id=second_id
    ).one()
    assert activation.event_metadata["deactivated_policy_version"] == 1
    assert activation.actor_id == "demo_user"

    budget = client.patch("/api/v1/policy/budget", json={"period_budget": 5000})
    assert budget.status_code == 200, budget.text
    budget_event = db_session.query(AuditLog).filter_by(
        action="POLICY_BUDGET_UPDATED", entity_id=second_id
    ).one()
    assert budget_event.changes["period_budget"] == {"before": 4500.0, "after": 5000.0}


def test_create_and_list_invoice(client, db_session):
    payload = {
        "id": "inv_test_01",
        "company_id": "co_demo_001",
        "beneficiary_id": "ben_test_01",
        "invoice_number": "T-001",
        "amount": "800.00",
        "currency": "USD",
        "issue_date": "2026-10-05",
        "due_date": "2026-11-04",
        "description": "Prueba",
        "source_type": "manual",
        "file_name": None,
        "file_hash": None,
        "extraction_confidence": 1.0,
        "raw_text": "texto de prueba",
    }
    response = client.post("/api/v1/invoices", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "inv_test_01"
    assert data["status"] == "PENDING"
    from app.models.audit_log import AuditLog

    upload_event = db_session.query(AuditLog).filter_by(
        action="INVOICE_UPLOADED", entity_id="inv_test_01"
    ).one()
    assert upload_event.actor_id == "demo_user"
    assert upload_event.event_metadata["amount"] == 800.0

    response = client.get("/api/v1/invoices/inv_test_01")
    assert response.status_code == 200
    assert response.json()["invoice_number"] == "T-001"
    assert response.json()["last_policy_version"] is None

    response = client.get("/api/v1/invoices?status=PENDING&company_id=co_demo_001")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["last_policy_version"] is None

    response = client.get("/api/v1/invoices?beneficiary_id=ben_test_01")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_invoice_list_includes_latest_decision_policy_version(client, db_session):
    from datetime import datetime

    from app.models.company import CompanyDemo
    from app.models.decision_record import DecisionRecord
    from app.models.invoice import Invoice

    db_session.add(CompanyDemo(id="co_last_version", name="Empresa", currency_base="USD"))
    db_session.add(
        Invoice(
            id="inv_last_version",
            company_id="co_last_version",
            source_type="manual",
            status="BLOCKED",
        )
    )
    db_session.add_all(
        [
            DecisionRecord(
                id="dec_last_v1",
                invoice_id="inv_last_version",
                policy_version=1,
                outcome="BLOCKED",
                reason_codes=[],
                rules_evaluated=[],
                created_at=datetime(2026, 1, 1),
            ),
            DecisionRecord(
                id="dec_last_v3",
                invoice_id="inv_last_version",
                policy_version=3,
                outcome="BLOCKED",
                reason_codes=[],
                rules_evaluated=[],
                created_at=datetime(2026, 1, 2),
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/invoices?company_id=co_last_version")
    assert response.status_code == 200, response.text
    assert response.json()[0]["last_policy_version"] == 3


def test_invoice_review_audit_uses_authenticated_actor(client, db_session):
    from app.models.audit_log import AuditLog
    from app.models.company import CompanyDemo
    from app.models.human_review import HumanReview
    from app.models.invoice import Invoice

    db_session.add(CompanyDemo(id="co_review_audit", name="Empresa", currency_base="USD"))
    db_session.add(
        Invoice(
            id="inv_review_audit",
            company_id="co_review_audit",
            source_type="manual",
            status="NEEDS_HUMAN_APPROVAL",
            invoice_number="FAC-REVIEW",
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/invoices/inv_review_audit/review",
        json={
            "action": "approve",
            "reason": "Verificación completada",
        },
    )
    assert response.status_code == 200, response.text
    review = db_session.query(HumanReview).filter_by(invoice_id="inv_review_audit").one()
    assert review.reviewer_demo_id == "demo_user"
    event = db_session.query(AuditLog).filter_by(
        action="INVOICE_APPROVED", entity_id="inv_review_audit"
    ).one()
    assert event.actor_id == "demo_user"
    assert event.event_metadata["reason"] == "Verificación completada"
    assert event.changes["status"] == {
        "before": "NEEDS_HUMAN_APPROVAL",
        "after": "APPROVED",
    }


def test_patch_invoice_corrections_sync_extracted_fields_and_reset_status(client, db_session):
    from app.models.beneficiary import Beneficiary
    from app.models.company import CompanyDemo
    from app.models.invoice import Invoice

    db_session.add(CompanyDemo(id="co_patch_01", name="Co Patch", currency_base="USD"))
    db_session.add(
        Beneficiary(
            id="ben_patch_01",
            company_id="co_patch_01",
            name="Mantenimiento Pacífico S.A.S.",
            normalized_name="mantenimiento pacifico sas",
            allowed=True,
        )
    )
    db_session.add(
        Invoice(
            id="inv_patch_01",
            company_id="co_patch_01",
            source_type="pdf",
            status="BLOCKED",
            extracted={"invoice_number": None, "_field_sources": {"amount": "pdf"}},
        )
    )
    db_session.commit()

    response = client.patch(
        "/api/v1/invoices/inv_patch_01",
        json={
            "beneficiary_name": "Mantenimiento Pacífico S.A.S.",
            "invoice_number": "MAN-204",
            "amount": "750.00",
            "currency": "USD",
            "issue_date": "2026-10-18",
            "due_date": "2026-11-18",
            "description": "Servicio de mantenimiento",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["beneficiary_id"] == "ben_patch_01"
    assert body["extracted"]["beneficiary_name"] == "Mantenimiento Pacífico S.A.S."
    assert body["extracted"]["invoice_number"] == "MAN-204"
    assert body["extracted"]["amount"] == "750.00"
    assert body["extracted"]["issue_date"] == "2026-10-18"
    assert body["extracted"]["due_date"] == "2026-11-18"
    assert body["extracted"]["description"] == "Servicio de mantenimiento"
    assert body["extracted"]["_field_sources"]["invoice_number"] == "manual"
    assert body["extracted"]["_field_sources"]["amount"] == "manual"
