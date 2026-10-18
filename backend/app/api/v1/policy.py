from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import DemoActor, get_demo_actor
from app.database import get_db
from app.models.policy import PaymentPolicy
from app.models.rule_action import RuleAction
from app.models.company import CompanyDemo
from app.models.policy_change_reason import PolicyChangeReason
from app.schemas.policy import BudgetUpdate, PaymentPolicyOut, PolicyCreate, PolicyActivate
from app.rules.catalog import RULE_CATALOG
from app.services.audit import (
    POLICY_ACTIVATED,
    POLICY_BUDGET_UPDATED,
    POLICY_CREATED,
    record_audit,
)

router = APIRouter()


@router.get("/catalog", tags=["policy"])
def get_policy_catalog():
    return RULE_CATALOG


@router.get("/versions", response_model=list[PaymentPolicyOut], tags=["policy"])
def list_policy_versions(db: Session = Depends(get_db)):
    return db.query(PaymentPolicy).order_by(PaymentPolicy.version.desc()).all()


@router.get("/", response_model=PaymentPolicyOut, tags=["policy"])
def get_active_policy(db: Session = Depends(get_db)):
    policy = db.query(PaymentPolicy).filter(PaymentPolicy.active == True).first()  # noqa: E712
    if not policy:
        raise HTTPException(status_code=404, detail="No hay política activa")
    return policy


@router.put("/", response_model=PaymentPolicyOut, tags=["policy"])
def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    user: DemoActor = Depends(get_demo_actor),
):
    company = db.query(CompanyDemo).filter(CompanyDemo.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    latest_policy = (
        db.query(PaymentPolicy)
        .filter(PaymentPolicy.company_id == payload.company_id)
        .order_by(PaymentPolicy.version.desc())
        .first()
    )
    previous_active = (
        db.query(PaymentPolicy)
        .filter(PaymentPolicy.company_id == payload.company_id, PaymentPolicy.active.is_(True))
        .first()
    )
    expected_version = (latest_policy.version if latest_policy else 0) + 1
    if payload.version != expected_version:
        raise HTTPException(
            status_code=422,
            detail=f"La siguiente versión debe ser v{expected_version}",
        )

    new_policy = PaymentPolicy(
        id=f"pol_{payload.company_id}_v{payload.version}",
        company_id=payload.company_id,
        version=payload.version,
        active=payload.activate,
        currency=payload.currency,
        max_invoice_amount=payload.max_invoice_amount,
        approval_threshold=payload.approval_threshold,
        period_budget=payload.period_budget,
        period_type=payload.period_type,
        period_basis=payload.period_basis,
        amount_tolerance_pct=payload.amount_tolerance_pct,
        min_extraction_confidence=payload.min_extraction_confidence,
        name_similarity_threshold=payload.name_similarity_threshold,
        possible_duplicate_date_window_days=payload.possible_duplicate_date_window_days,
    )
    db.add(new_policy)

    if payload.activate:
        db.query(PaymentPolicy).filter(
            PaymentPolicy.company_id == payload.company_id,
            PaymentPolicy.id != new_policy.id,
        ).update({PaymentPolicy.active: False})

    db.flush()
    db.add(PolicyChangeReason(policy_id=new_policy.id, reason=payload.change_reason))
    for ra in payload.rule_actions:
        db.add(RuleAction(code=ra.code, policy_id=new_policy.id, action=ra.action))

    previous_values = _policy_values(latest_policy, db) if latest_policy else {}
    next_values = _policy_values_from_payload(payload)
    changes = {
        key: {"before": previous_values.get(key), "after": value}
        for key, value in next_values.items()
        if previous_values.get(key) != value
    }
    record_audit(
        db,
        actor=user,
        action=POLICY_CREATED,
        entity_type="policy",
        entity_id=new_policy.id,
        entity_label=f"Política v{new_policy.version}",
        summary=f"{user.full_name} creó la política v{new_policy.version}",
        changes=changes,
        metadata={"change_reason": payload.change_reason},
        company_id=payload.company_id,
    )
    if payload.activate:
        record_audit(
            db,
            actor=user,
            action=POLICY_ACTIVATED,
            entity_type="policy",
            entity_id=new_policy.id,
            entity_label=f"Política v{new_policy.version}",
            summary=f"{user.full_name} activó la política v{new_policy.version}",
            changes={
                "active_policy": {
                    "before": previous_active.id if previous_active else None,
                    "after": new_policy.id,
                }
            },
            metadata={
                "policy_version": new_policy.version,
                "deactivated_policy_id": previous_active.id if previous_active else None,
                "deactivated_policy_version": previous_active.version if previous_active else None,
            },
            company_id=payload.company_id,
        )

    db.commit()
    db.refresh(new_policy)
    return new_policy


@router.post("/activate", tags=["policy"])
def activate_policy(
    payload: PolicyActivate,
    db: Session = Depends(get_db),
    user: DemoActor = Depends(get_demo_actor),
):
    policy = db.query(PaymentPolicy).filter(PaymentPolicy.id == payload.policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    previous_active = (
        db.query(PaymentPolicy)
        .filter(
            PaymentPolicy.company_id == policy.company_id,
            PaymentPolicy.active.is_(True),
        )
        .first()
    )
    db.query(PaymentPolicy).filter(PaymentPolicy.company_id == policy.company_id).update(
        {PaymentPolicy.active: False}
    )
    policy.active = True
    record_audit(
        db,
        actor=user,
        action=POLICY_ACTIVATED,
        entity_type="policy",
        entity_id=policy.id,
        entity_label=f"Política v{policy.version}",
        summary=f"{user.full_name} activó la política v{policy.version}",
        changes={
            "active_policy": {
                "before": previous_active.id if previous_active else None,
                "after": policy.id,
            }
        },
        metadata={
            "policy_version": policy.version,
            "deactivated_policy_id": previous_active.id if previous_active else None,
            "deactivated_policy_version": previous_active.version if previous_active else None,
        },
        company_id=policy.company_id,
    )
    db.commit()
    return {"policy_id": policy.id, "active": True}


@router.patch("/budget", response_model=PaymentPolicyOut, tags=["policy"])
def update_active_budget(
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    user: DemoActor = Depends(get_demo_actor),
):
    if payload.period_budget < 0:
        raise HTTPException(status_code=422, detail="El presupuesto no puede ser negativo")

    policy = db.query(PaymentPolicy).filter(PaymentPolicy.active.is_(True)).first()
    if not policy:
        raise HTTPException(status_code=404, detail="No hay política activa")

    previous_budget = policy.period_budget
    next_budget = float(payload.period_budget)
    policy.period_budget = next_budget
    if previous_budget != next_budget:
        record_audit(
            db,
            actor=user,
            action=POLICY_BUDGET_UPDATED,
            entity_type="policy",
            entity_id=policy.id,
            entity_label=f"Política v{policy.version}",
            summary=f"{user.full_name} actualizó el presupuesto de la política v{policy.version}",
            changes={"period_budget": {"before": previous_budget, "after": next_budget}},
            metadata={"policy_version": policy.version},
            company_id=policy.company_id,
        )
    db.commit()
    db.refresh(policy)
    return policy


def _policy_values(policy: PaymentPolicy, db: Session) -> dict[str, object]:
    rule_actions = {
        item.code: item.action
        for item in db.query(RuleAction).filter(RuleAction.policy_id == policy.id).all()
    }
    return {
        "currency": policy.currency,
        "max_invoice_amount": _decimal_text(policy.max_invoice_amount),
        "approval_threshold": _decimal_text(policy.approval_threshold),
        "period_budget": _decimal_text(policy.period_budget),
        "period_type": policy.period_type,
        "period_basis": policy.period_basis,
        "amount_tolerance_pct": _decimal_text(policy.amount_tolerance_pct),
        "min_extraction_confidence": policy.min_extraction_confidence,
        "name_similarity_threshold": policy.name_similarity_threshold,
        "possible_duplicate_date_window_days": policy.possible_duplicate_date_window_days,
        "rule_actions": rule_actions,
    }


def _decimal_text(value: object) -> str:
    return format(Decimal(str(value)).normalize(), "f")


def _policy_values_from_payload(payload: PolicyCreate) -> dict[str, object]:
    return {
        "currency": payload.currency,
        "max_invoice_amount": _decimal_text(payload.max_invoice_amount),
        "approval_threshold": _decimal_text(payload.approval_threshold),
        "period_budget": _decimal_text(payload.period_budget),
        "period_type": payload.period_type,
        "period_basis": payload.period_basis,
        "amount_tolerance_pct": _decimal_text(payload.amount_tolerance_pct),
        "min_extraction_confidence": payload.min_extraction_confidence,
        "name_similarity_threshold": payload.name_similarity_threshold,
        "possible_duplicate_date_window_days": payload.possible_duplicate_date_window_days,
        "rule_actions": {item.code: item.action for item in payload.rule_actions},
    }
