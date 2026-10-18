def test_list_empty_beneficiaries(client):
    response = client.get("/api/v1/beneficiaries")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_beneficiary(client):
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


def test_update_missing_beneficiary_returns_not_found(client, db_session):
    response = client.patch(
        "/api/v1/beneficiaries/no-existe",
        json={"name": "Proveedor"},
    )

    assert response.status_code == 404


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


def test_create_and_list_invoice(client):
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

    response = client.get("/api/v1/invoices/inv_test_01")
    assert response.status_code == 200
    assert response.json()["invoice_number"] == "T-001"

    response = client.get("/api/v1/invoices?status=PENDING&company_id=co_demo_001")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/api/v1/invoices?beneficiary_id=ben_test_01")
    assert response.status_code == 200
    assert len(response.json()) == 1


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
