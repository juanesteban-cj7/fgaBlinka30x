import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.app_user import AppUser
from app.models.invoice import Invoice
from app.models.human_review import HumanReview
from app.models.beneficiary import Beneficiary
from app.rules.normalization import norm_name
from app.schemas.invoice import InvoiceOut, InvoiceCreate, InvoiceUpdate
from app.services.audit import INVOICE_APPROVED, INVOICE_REJECTED, INVOICE_UPLOADED, record_audit
from app.services.invoice_numbering import next_invoice_number

router = APIRouter()


class HumanReviewRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    reason: str = Field(min_length=1, max_length=2000)


@router.get("/", response_model=list[InvoiceOut], tags=["invoices"])
def list_invoices(
    company_id: str | None = None,
    status: str | None = None,
    beneficiary_id: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Invoice).options(selectinload(Invoice.decisions))
    if company_id:
        query = query.filter(Invoice.company_id == company_id)
    if status:
        query = query.filter(Invoice.status == status)
    if beneficiary_id:
        query = query.filter(Invoice.beneficiary_id == beneficiary_id)
    return query.order_by(Invoice.created_at.desc()).all()


@router.post("/", response_model=InvoiceOut, status_code=201, tags=["invoices"])
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_current_user),
):
    existing = db.query(Invoice).filter(Invoice.id == payload.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="La factura ya existe")
    invoice = Invoice(**payload.model_dump())
    db.add(invoice)
    label = invoice.invoice_number or invoice.id
    record_audit(
        db,
        actor=user,
        action=INVOICE_UPLOADED,
        entity_type="invoice",
        entity_id=invoice.id,
        entity_label=label,
        summary=f"{user.full_name} cargó la factura {label}",
        metadata={
            "file_name": invoice.file_name,
            "file_hash": invoice.file_hash,
            "beneficiary_id": invoice.beneficiary_id,
            "amount": float(invoice.amount) if invoice.amount is not None else None,
            "currency": invoice.currency,
            "source_type": invoice.source_type,
        },
        company_id=invoice.company_id,
    )
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceOut, tags=["invoices"])
def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceOut, tags=["invoices"])
def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    _user: AppUser = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    previous_invoice_number = invoice.invoice_number
    update_values = payload.model_dump(
        exclude_unset=True,
        exclude={"standardize_number", "beneficiary_name"},
    )
    extracted = dict(invoice.extracted or {})
    field_sources_value = extracted.get("_field_sources")
    field_sources = dict(field_sources_value) if isinstance(field_sources_value, dict) else {}
    corrected_fields = {
        "invoice_number",
        "amount",
        "currency",
        "issue_date",
        "due_date",
        "description",
    }
    for field, value in update_values.items():
        setattr(invoice, field, value)

        if field == "beneficiary_id":
            beneficiary = (
                db.query(Beneficiary)
                .filter(
                    Beneficiary.id == value,
                    Beneficiary.company_id == invoice.company_id,
                )
                .first()
            ) if value else None
            if value and not beneficiary:
                raise HTTPException(status_code=422, detail="El beneficiario no pertenece a la empresa")
            extracted["beneficiary_name"] = beneficiary.name if beneficiary else None
            field_sources["beneficiary_name"] = "manual"
            corrected_fields.add("beneficiary_name")
        elif field in corrected_fields:
            if isinstance(value, (date, Decimal)):
                extracted[field] = value.isoformat() if isinstance(value, date) else str(value)
            else:
                extracted[field] = value
            field_sources[field] = "manual"

    if "beneficiary_name" in payload.model_fields_set:
        beneficiary_name = payload.beneficiary_name
        beneficiary = None
        if beneficiary_name:
            beneficiary = (
                db.query(Beneficiary)
                .filter(
                    Beneficiary.company_id == invoice.company_id,
                    Beneficiary.normalized_name == norm_name(beneficiary_name),
                )
                .first()
            )
        invoice.beneficiary_id = beneficiary.id if beneficiary else None
        extracted["beneficiary_name"] = beneficiary_name
        field_sources["beneficiary_name"] = "manual"
        corrected_fields.add("beneficiary_name")

    if payload.standardize_number:
        try:
            invoice.invoice_number = next_invoice_number(
                db, invoice.company_id, invoice.id, previous_invoice_number
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        extracted["invoice_number"] = invoice.invoice_number
        field_sources["invoice_number"] = "manual"
        corrected_fields.add("invoice_number")

    if corrected_fields.intersection(update_values) or "beneficiary_name" in payload.model_fields_set or payload.standardize_number:
        extracted["_field_sources"] = field_sources
        invoice.extracted = extracted
        invoice.status = "PENDING"

    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/review", tags=["invoices"])
def review_invoice(
    invoice_id: str,
    payload: HumanReviewRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if invoice.status != "NEEDS_HUMAN_APPROVAL":
        raise HTTPException(status_code=409, detail="La factura no está pendiente de aprobación humana")
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="La justificación es obligatoria")

    review = HumanReview(
        id=f"review_{uuid.uuid4().hex[:12]}",
        invoice_id=invoice.id,
        reviewer_demo_id=user.id,
        action=payload.action,
        reason=reason,
    )
    invoice.status = "APPROVED" if payload.action == "approve" else "REJECTED"
    db.add(review)
    approved = payload.action == "approve"
    label = invoice.invoice_number or invoice.id
    record_audit(
        db,
        actor=user,
        action=INVOICE_APPROVED if approved else INVOICE_REJECTED,
        entity_type="invoice",
        entity_id=invoice.id,
        entity_label=label,
        summary=f"{user.full_name} {'aprobó' if approved else 'rechazó'} la factura {label}",
        changes={"status": {"before": "NEEDS_HUMAN_APPROVAL", "after": invoice.status}},
        metadata={"reason": reason},
        company_id=invoice.company_id,
    )
    db.commit()
    return {"invoice_id": invoice.id, "status": invoice.status, "action": payload.action, "reason": reason}
