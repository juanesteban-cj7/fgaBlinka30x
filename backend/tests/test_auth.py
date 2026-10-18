def test_login_and_current_user(client, unauthenticated_client):
    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "test.user", "password": "test-password"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["username"] == "test.user"
    assert "password_hash" not in response.json()["user"]
    assert client.get("/api/v1/auth/me").json()["id"] == "test_user_01"


def test_auth_rejects_invalid_password(unauthenticated_client):
    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "test.user", "password": "incorrecto"},
    )

    assert response.status_code == 401


def test_auth_required_for_data_modifications(unauthenticated_client):
    from app.rules.catalog import RULE_CATALOG

    requests = [
        ("post", "/api/v1/beneficiaries", {
            "id": "ben_auth_test",
            "company_id": "co_demo_001",
            "name": "Beneficiario",
            "normalized_name": "beneficiario",
        }),
        ("patch", "/api/v1/beneficiaries/no-existe", {}),
        ("delete", "/api/v1/beneficiaries/no-existe", None),
        ("post", "/api/v1/invoices", {
            "id": "inv_auth_test",
            "company_id": "co_demo_001",
            "source_type": "manual",
        }),
        ("patch", "/api/v1/invoices/no-existe", {}),
        ("post", "/api/v1/invoices/no-existe/review", {
            "action": "approve",
            "reason": "Revisión",
        }),
        ("post", "/api/v1/invoices/no-existe/evaluate", None),
        ("put", "/api/v1/policy/", {
            "company_id": "co_demo_001",
            "version": 1,
            "currency": "USD",
            "max_invoice_amount": 5000,
            "approval_threshold": 1000,
            "period_budget": 12000,
            "period_type": "monthly",
            "period_basis": "issue_date",
            "rule_actions": [
                {"code": item["code"], "action": item["default_action"]}
                for item in RULE_CATALOG
            ],
            "change_reason": "Prueba de autenticación",
            "activate": True,
        }),
        ("patch", "/api/v1/policy/budget", {"period_budget": 100}),
        ("post", "/api/v1/policy/activate", {"policy_id": "no-existe"}),
    ]

    for method, url, body in requests:
        response = unauthenticated_client.request(method.upper(), url, json=body)
        assert response.status_code == 401, (method, url, response.text)


def test_auth_required_for_upload_and_reextraction(unauthenticated_client):
    response = unauthenticated_client.post(
        "/api/v1/invoices/upload",
        files={"file": ("invoice.pdf", b"%PDF-1.4 fake", "application/pdf")},
        data={"company_id": "co_demo_001"},
    )
    assert response.status_code == 401, response.text

    response = unauthenticated_client.post("/api/v1/invoices/no-existe/extract")
    assert response.status_code == 401, response.text

    response = unauthenticated_client.get("/api/v1/audit-log")
    assert response.status_code == 401, response.text
