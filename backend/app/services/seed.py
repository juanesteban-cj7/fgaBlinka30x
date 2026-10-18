"""Carga los datos ficticios de la Fase 1 en PostgreSQL.

Ejecutar desde la raíz del proyecto:
    PYTHONPATH=backend python -m app.services.seed
"""
import json
from pathlib import Path
from decimal import Decimal

from app.database import SessionLocal, engine, Base
import app.models  # noqa: F401  registra modelos en Base.metadata

BASE = Path(__file__).resolve().parents[3]  # raíz del repositorio (fgaBlinka30x)
DEMO = BASE / "data-demo"


def seed(db):
    cfg = json.loads((DEMO / "demo-config.json").read_text(encoding="utf-8"))
    company = cfg["company"]
    pol = cfg["policy"]

    from app.models.agreement import Agreement
    from app.models.beneficiary import Beneficiary
    from app.models.budget_reservation import BudgetReservation
    from app.models.company import CompanyDemo
    from app.models.invoice import Invoice
    from app.models.policy import PaymentPolicy
    from app.models.rule_action import RuleAction

    if db.query(CompanyDemo).filter(CompanyDemo.id == company["id"]).first():
        print("Seed ya aplicado: se conservan los datos existentes.")
        return

    c = CompanyDemo(
        id=company["id"],
        name=company["name"],
        currency_base=company["currency_base"],
    )
    db.add(c)

    p = PaymentPolicy(
        id=f"pol_v{pol['version']}",
        company_id=company["id"],
        version=pol["version"],
        active=pol["active"],
        currency=pol["currency"],
        max_invoice_amount=float(Decimal(pol["max_invoice_amount"])),
        approval_threshold=float(Decimal(pol["approval_threshold"])),
        period_budget=float(Decimal(pol["period_budget"])),
        period_type=pol["period_type"],
        period_basis=pol["period_basis"],
        amount_tolerance_pct=float(Decimal(str(pol.get("amount_tolerance_pct", "0")))),
        min_extraction_confidence=pol.get("min_extraction_confidence", 0.80),
        name_similarity_threshold=pol.get("name_similarity_threshold", 0.85),
        possible_duplicate_date_window_days=pol.get(
            "possible_duplicate_date_window_days", 0
        ),
    )
    db.add(p)
    db.flush()
    for code, action in pol["rule_actions"].items():
        db.add(RuleAction(code=code, policy_id=p.id, action=action))

    for b in cfg["beneficiaries"]:
        db.add(
            Beneficiary(
                id=b["id"],
                company_id=company["id"],
                name=b["name"],
                normalized_name=b["normalized_name"],
                allowed=b["allowed"],
                reference_code=b.get("reference_code"),
                category=b.get("category"),
            )
        )

    for a in cfg["agreements"]:
        db.add(
            Agreement(
                id=a["id"],
                company_id=company["id"],
                beneficiary_id=a["beneficiary_id"],
                description=a["description"],
                expected_amount=float(Decimal(a["expected_amount"])),
                currency=a["currency"],
                valid_from=a["valid_from"],
                valid_to=a["valid_to"],
            )
        )

    for h in cfg["history_invoices"]:
        db.add(
            Invoice(
                id=h["id"],
                company_id=company["id"],
                beneficiary_id=h["beneficiary_id"],
                invoice_number=h["invoice_number"],
                amount=float(Decimal(h["amount"])),
                currency=h["currency"],
                issue_date=h["issue_date"],
                due_date=h.get("due_date"),
                description=None,
                source_type="history",
                file_hash=h["file_hash"],
                extraction_confidence=1.0,
                status=h["status"],
            )
        )
        if h.get("reserves_budget"):
            db.add(
                BudgetReservation(
                    id=f"res_{h['id']}",
                    invoice_id=h["id"],
                    company_id=company["id"],
                    period_key=h["issue_date"][:7],
                    amount=float(Decimal(h["amount"])),
                    currency=h["currency"],
                    status="reserved",
                )
            )

    db.commit()
    print("Seed completado: empresa, política v1, beneficiarios, acuerdos, facturas históricas y reservas de presupuesto.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
