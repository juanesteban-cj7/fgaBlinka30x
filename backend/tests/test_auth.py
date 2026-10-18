def test_api_is_available_without_authentication(client, unauthenticated_client):
    assert unauthenticated_client.get("/api/v1/invoices").status_code == 200
    assert unauthenticated_client.get("/api/v1/audit-log").status_code == 200

    response = unauthenticated_client.post(
        "/api/v1/beneficiaries",
        json={
            "id": "ben_without_login",
            "company_id": "co_demo_001",
            "name": "Proveedor sin login",
        },
    )
    assert response.status_code == 201, response.text


def test_auth_endpoints_are_not_exposed(unauthenticated_client):
    assert unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "demo", "password": "demo"},
    ).status_code == 404
    assert unauthenticated_client.get("/api/v1/auth/me").status_code == 404
