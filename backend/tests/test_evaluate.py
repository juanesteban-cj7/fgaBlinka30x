from decimal import Decimal
from datetime import date

from conftest import TestingSessionLocal
from app.models.company import CompanyDemo


def _d(s):
    return date.fromisoformat(s) if s else None
from app.models.policy import PaymentPolicy
from app.models.rule_action import RuleAction
from app.models.beneficiary import Beneficiary
from app.models.agreement import Agreement
from app.models.invoice import Invoice


def _seed_policy(db):
    db.add(CompanyDemo(id="co_demo_001", name="Co Demo", currency_base="USD"))
    db.add(PaymentPolicy(
        id="pol_v1", company_id="co_demo_001", version=1, active=True,
        currency="USD", max_invoice_amount=5000.00, approval_threshold=1000.00,
        period_budget=12000.00, period_type="monthly", period_basis="issue_date",
    ))
    db.add(RuleAction(code="DUPLICATE_CONFIRMED", policy_id="pol_v1", action="BLOCKED"))
    db.add(RuleAction(code="POSSIBLE_DUPLICATE", policy_id="pol_v1", action="NEEDS_HUMAN_APPROVAL"))
    db.add(RuleAction(code="BENEFICIARY_NOT_ALLOWED", policy_id="pol_v1", action="BLOCKED"))
    db.add(RuleAction(code="BENEFICIARY_UNKNOWN", policy_id="pol_v1", action="BLOCKED"))
    db.add(RuleAction(code="BENEFICIARY_NAME_AMBIGUOUS", policy_id="pol_v1", action="NEEDS_HUMAN_APPROVAL"))
    db.add(RuleAction(code="CURRENCY_MISMATCH", policy_id="pol_v1", action="NEEDS_HUMAN_APPROVAL"))
    db.add(RuleAction(code="AGREEMENT_EXPIRED", policy_id="pol_v1", action="NEEDS_HUMAN_APPROVAL"))
    db.add(RuleAction(code="AGREEMENT_AMOUNT_MISMATCH", policy_id="pol_v1", action="NEEDS_HUMAN_APPROVAL"))
    db.add(RuleAction(code="ABOVE_MAX_INVOICE", policy_id="pol_v1", action="BLOCKED"))
    db.add(RuleAction(code="BUDGET_EXCEEDED", policy_id="pol_v1", action="BLOCKED"))
    db.add(RuleAction(code="ABOVE_APPROVAL_THRESHOLD", policy_id="pol_v1", action="NEEDS_HUMAN_APPROVAL"))
    db.add(RuleAction(code="MISSING_REQUIRED_FIELDS", policy_id="pol_v1", action="NEEDS_HUMAN_APPROVAL"))
    db.add(RuleAction(code="INVALID_FIELD", policy_id="pol_v1", action="NEEDS_HUMAN_APPROVAL"))
    db.add(RuleAction(code="LOW_EXTRACTION_CONFIDENCE", policy_id="pol_v1", action="NEEDS_HUMAN_APPROVAL"))
    db.add(Beneficiary(id="ben_001", company_id="co_demo_001", name="Suministros Andinos Ltda",
                       normalized_name="suministros andinos ltda", allowed=True))
    db.add(Beneficiary(id="ben_003", company_id="co_demo_001", name="Tecnoservicios Caribe S.A.S.",
                       normalized_name="tecnoservicios caribe sas", allowed=True))
    db.add(Beneficiary(id="ben_008", company_id="co_demo_001", name="Eventos Horizonte S.A.S.",
                       normalized_name="eventos horizonte sas", allowed=False))
    db.add(Agreement(id="agr_001", company_id="co_demo_001", beneficiary_id="ben_001",
                     description="insumos", expected_amount=800.00, currency="USD",
                     valid_from=_d("2026-01-01"), valid_to=_d("2026-12-31")))
    db.add(Agreement(id="agr_003", company_id="co_demo_001", beneficiary_id="ben_003",
                     description="soporte", expected_amount=1450.00, currency="USD",
                     valid_from=_d("2026-01-01"), valid_to=_d("2026-12-31")))
    db.commit()


def test_evaluate_eligible_reserves_budget(client, db_session):
    from app.models.audit_log import AuditLog

    _seed_policy(db_session)
    db_session.add(Invoice(
        id="inv_eval_01", company_id="co_demo_001", beneficiary_id="ben_001",
        invoice_number="T-001", amount=800.00, currency="USD",
        issue_date=_d("2026-10-05"), due_date=_d("2026-11-04"),
        description="insumos", source_type="manual",
        file_hash=None, extraction_confidence=1.0,
        raw_text=None, status="PENDING",
        extracted={"beneficiary_name": "Suministros Andinos Ltda", "invoice_number": "T-001",
                   "amount": "800.00", "currency": "USD", "issue_date": "2026-10-05",
                   "due_date": "2026-11-04", "description": "insumos"},
    ))
    db_session.commit()

    r = client.post("/api/v1/invoices/inv_eval_01/evaluate")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["outcome"] == "ELIGIBLE_SIMULATED"
    assert data["reserved_budget"] is True
    assert data["reason_codes"] == ["ALL_CHECKS_PASSED"]
    event = db_session.query(AuditLog).filter_by(
        action="INVOICE_EVALUATED", entity_id="inv_eval_01"
    ).one()
    assert event.actor_id == "test_user_01"
    assert event.event_metadata == {
        "outcome": "ELIGIBLE_SIMULATED",
        "policy_version": 1,
        "reason_codes": ["ALL_CHECKS_PASSED"],
    }

    r2 = client.get("/api/v1/invoices/inv_eval_01/decisions")
    assert r2.status_code == 200
    assert len(r2.json()) == 1
    assert r2.json()[0]["outcome"] == "ELIGIBLE_SIMULATED"


def test_evaluate_blocked_duplicate(client, db_session):
    _seed_policy(db_session)
    db_session.add(Invoice(
        id="hist_dup", company_id="co_demo_001", beneficiary_id="ben_001",
        invoice_number="SA-2026-0412", amount=800.00, currency="USD",
        issue_date=_d("2026-09-03"), due_date=_d("2026-10-03"), description=None,
        source_type="history", file_hash="sha256:hist01", extraction_confidence=1.0,
        raw_text=None, status="ELIGIBLE_SIMULATED",
        extracted={"beneficiary_name": "Suministros Andinos Ltda", "invoice_number": "SA-2026-0412",
                   "amount": "800.00", "currency": "USD", "issue_date": "2026-09-03",
                   "due_date": "2026-10-03", "description": None},
    ))
    db_session.commit()

    db_session.add(Invoice(
        id="inv_eval_dup", company_id="co_demo_001", beneficiary_id="ben_001",
        invoice_number="SA-2026-0412", amount=800.00, currency="USD",
        issue_date=_d("2026-10-08"), due_date=_d("2026-11-07"), description=None,
        source_type="pdf", file_hash="sha256:demo004", extraction_confidence=0.97,
        raw_text=None, status="PENDING",
        extracted={"beneficiary_name": "Suministros Andinos Ltda", "invoice_number": "SA-2026-0412",
                   "amount": "800.00", "currency": "USD", "issue_date": "2026-10-08",
                   "due_date": "2026-11-07", "description": None},
    ))
    db_session.commit()

    r = client.post("/api/v1/invoices/inv_eval_dup/evaluate")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["outcome"] == "BLOCKED"
    assert "DUPLICATE_CONFIRMED" in data["reason_codes"]
    assert data["linked_invoice_id"] == "hist_dup"
    assert data["reserved_budget"] is False
