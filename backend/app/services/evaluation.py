import uuid
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import TYPE_CHECKING

from app.database import SessionLocal
from app.models.invoice import Invoice
from app.models.decision_record import DecisionRecord
from app.models.budget_reservation import BudgetReservation
from app.models.policy import PaymentPolicy
from app.models.rule_action import RuleAction
from app.models.beneficiary import Beneficiary
from app.models.agreement import Agreement
from app.rules.engine import evaluate
from app.services.audit import INVOICE_EVALUATED, record_audit

if TYPE_CHECKING:
    from app.api.deps import DemoActor


def _reservations_by_period(db: Session, company_id: str):
    rows = (
        db.query(BudgetReservation.period_key, func.sum(BudgetReservation.amount))
        .filter(BudgetReservation.company_id == company_id)
        .group_by(BudgetReservation.period_key)
        .all()
    )
    return {period: Decimal(str(total or 0)) for period, total in rows}


def evaluate_and_record(db: Session, invoice_id: str, actor: "DemoActor | None" = None):
    invoice = (
        db.query(Invoice)
        .options(joinedload(Invoice.company))
        .filter(Invoice.id == invoice_id)
        .first()
    )
    if not invoice:
        return None

    policy = (
        db.query(PaymentPolicy)
        .filter(PaymentPolicy.company_id == invoice.company_id, PaymentPolicy.active == True)  # noqa: E712
        .first()
    )
    if not policy:
        return None

    rule_actions_map = {ra.code: ra.action for ra in policy.rule_actions}

    beneficiaries = db.query(Beneficiary).filter(Beneficiary.company_id == invoice.company_id).all()

    agreements = db.query(Agreement).filter(Agreement.company_id == invoice.company_id).all()
    agreements_map = {a.beneficiary_id: a for a in agreements}

    all_invoices = db.query(Invoice).filter(Invoice.company_id == invoice.company_id).all()

    reservations = _reservations_by_period(db, invoice.company_id)

    result = evaluate(invoice, policy, beneficiaries, agreements_map, all_invoices, reservations,
                      rule_actions=rule_actions_map)

    explanation = _build_explanation(result, invoice, policy, beneficiaries, agreements_map)
    result.explanation = explanation

    invoice.status = result.outcome
    db.add(invoice)

    decision = DecisionRecord(
        id=str(uuid.uuid4()),
        invoice_id=invoice.id,
        policy_version=result.policy_version or policy.version,
        outcome=result.outcome,
        reason_codes=result.reason_codes,
        explanation=explanation,
        rules_evaluated=result.rules_evaluated,
    )
    db.add(decision)

    if result.reserved_budget and invoice.amount is not None and invoice.currency and invoice.issue_date:
        period = str(invoice.issue_date)[:7]
        existing = (
            db.query(BudgetReservation)
            .filter(BudgetReservation.invoice_id == invoice.id)
            .first()
        )
        if not existing:
            db.add(
                BudgetReservation(
                    id=str(uuid.uuid4()),
                    invoice_id=invoice.id,
                    company_id=invoice.company_id,
                    period_key=period,
                    amount=float(Decimal(str(invoice.amount))),
                    currency=invoice.currency,
                    status="reserved",
                )
            )

    if actor:
        label = invoice.invoice_number or invoice.id
        record_audit(
            db,
            actor=actor,
            action=INVOICE_EVALUATED,
            entity_type="invoice",
            entity_id=invoice.id,
            entity_label=label,
            summary=f"{actor.full_name} evaluó la factura {label}: {result.outcome}",
            metadata={
                "outcome": result.outcome,
                "policy_version": result.policy_version or policy.version,
                "reason_codes": result.reason_codes,
            },
            company_id=invoice.company_id,
        )

    db.commit()
    db.refresh(invoice)
    db.refresh(decision)
    return {
        "invoice_id": invoice.id,
        "outcome": result.outcome,
        "reason_codes": result.reason_codes,
        "explanation": explanation,
        "reserved_budget": result.reserved_budget,
        "linked_invoice_id": result.linked_invoice_id,
        "policy_version": result.policy_version,
        "rules_evaluated": result.rules_evaluated,
        "decision_id": decision.id,
    }


def _build_explanation(result, invoice, policy, beneficiaries, agreements_map):
    ex = invoice.extracted or {}
    parts = []
    if result.outcome == "ELIGIBLE_SIMULATED":
        parts.append("La factura pasó todas las reglas y es apta para pago simulado.")
    elif result.outcome == "BLOCKED":
        parts.append("La factura fue frenada porque no cumple una o más reglas obligatorias.")
    else:
        parts.append("La factura requiere aprobación humana por una excepción prevista en la política.")

    if result.reason_codes and result.reason_codes != ["ALL_CHECKS_PASSED"]:
        partes_motivos = []
        for code in result.reason_codes:
            partes_motivos.append(code)
        parts.append("Motivos: " + ", ".join(partes_motivos).replace("_", " ").title())

    amount = ex.get("amount")
    ccy = ex.get("currency")
    if amount and ccy:
        parts.append(f"Importe evaluado: {amount} {ccy}.")

    return " ".join(parts)
