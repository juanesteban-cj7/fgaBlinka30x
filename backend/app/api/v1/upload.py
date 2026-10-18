"""Endpoints de ingesta de documentos (Fase 4).

- POST /invoices/upload : sube un PDF o imagen, extrae texto y crea una factura PENDING.
- POST /invoices/{id}/extract : re-ejecuta la extracción sobre el archivo ya subido.

Los datos son 100% ficticios. No se ejecutan pagos.
"""
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.app_user import AppUser
from app.models.beneficiary import Beneficiary
from app.models.company import CompanyDemo
from app.models.invoice import Invoice
from app.rules.normalization import norm_name
from app.schemas.invoice import InvoiceUploadOut
from app.services.extraction import ExtractionResult, extract_file
from app.services.audit import INVOICE_UPLOADED, record_audit

router = APIRouter()


def _field_text(fields: dict[str, object | None], name: str) -> str | None:
    value = fields.get(name)
    return value if isinstance(value, str) else None


def _apply_extraction(
    invoice: Invoice,
    extracted: ExtractionResult,
    db: Session,
    beneficiary: Beneficiary | None = None,
    manual_values: dict[str, str | Decimal | date | None] | None = None,
) -> None:
    fields = dict(extracted.fields)
    source = "ocr" if extracted.ocr_used else extracted.source_type
    field_sources = {
        name: source for name in (
            "beneficiary_name",
            "invoice_number",
            "amount",
            "currency",
            "issue_date",
            "due_date",
            "description",
        )
    }
    if manual_values:
        for name, value in manual_values.items():
            if value is None:
                continue
            fields[name] = value.isoformat() if isinstance(value, date) else str(value)
            field_sources[name] = "manual"

    if beneficiary:
        fields["beneficiary_name"] = beneficiary.name
        field_sources["beneficiary_name"] = "manual"

    fields["_field_sources"] = field_sources
    invoice.extracted = fields
    invoice.invoice_number = _field_text(fields, "invoice_number")
    amount = _field_text(fields, "amount")
    invoice.amount = float(amount) if amount is not None else None
    invoice.currency = _field_text(fields, "currency")
    issue_date = _field_text(fields, "issue_date")
    invoice.issue_date = date.fromisoformat(issue_date) if issue_date else None
    due_date = _field_text(fields, "due_date")
    invoice.due_date = date.fromisoformat(due_date) if due_date else None
    invoice.description = _field_text(fields, "description") or ""

    if beneficiary:
        invoice.beneficiary_id = beneficiary.id
        return

    beneficiary_name = _field_text(fields, "beneficiary_name")
    matching_beneficiary = None
    if beneficiary_name:
        matching_beneficiary = (
            db.query(Beneficiary)
            .filter(
                Beneficiary.company_id == invoice.company_id,
                Beneficiary.normalized_name == norm_name(beneficiary_name),
            )
            .first()
        )
    invoice.beneficiary_id = matching_beneficiary.id if matching_beneficiary else None


@router.post("/upload", response_model=InvoiceUploadOut, status_code=201, tags=["invoices"])
async def upload_invoice(
    file: UploadFile = File(...),
    company_id: str | None = Form(None),
    beneficiary_id: str | None = Form(None),
    invoice_number: str | None = Form(None),
    amount: Decimal | None = Form(None),
    currency: str | None = Form(None),
    issue_date: date | None = Form(None),
    due_date: date | None = Form(None),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_current_user),
):
    resolved_company_id: str
    beneficiary = None
    if beneficiary_id:
        beneficiary = (
            db.query(Beneficiary)
            .filter(Beneficiary.id == beneficiary_id)
            .first()
        )
        if not beneficiary:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        if company_id and company_id != beneficiary.company_id:
            raise HTTPException(
                status_code=400,
                detail="El proveedor no pertenece a la empresa indicada",
            )
        resolved_company_id = beneficiary.company_id
    elif company_id:
        company = db.query(CompanyDemo).filter(CompanyDemo.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        resolved_company_id = company_id
    else:
        companies = db.query(CompanyDemo).order_by(CompanyDemo.id).limit(2).all()
        if len(companies) != 1:
            raise HTTPException(
                status_code=422,
                detail="No se puede determinar una empresa única; indique la empresa.",
            )
        resolved_company_id = companies[0].id

    content = await file.read()
    try:
        extracted = extract_file(content, file.filename or "archivo")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    invoice = Invoice(
        id=invoice_id,
        company_id=resolved_company_id,
        beneficiary_id=None,
        invoice_number=None,
        amount=None,
        currency=None,
        issue_date=None,
        due_date=None,
        description=None,
        source_type=extracted.source_type,
        file_name=extracted.file_name,
        file_hash=extracted.file_hash,
        file_path=extracted.file_path,
        extraction_confidence=extracted.extraction_confidence,
        raw_text=extracted.raw_text,
        extracted=None,
        status="PENDING",
    )
    _apply_extraction(
        invoice,
        extracted,
        db,
        beneficiary=beneficiary,
        manual_values={
            "invoice_number": invoice_number,
            "amount": amount,
            "currency": currency,
            "issue_date": issue_date,
            "due_date": due_date,
            "description": description,
        },
    )
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
            "amount": invoice.amount,
            "currency": invoice.currency,
            "source_type": invoice.source_type,
        },
        company_id=invoice.company_id,
    )
    db.commit()
    db.refresh(invoice)

    return InvoiceUploadOut(
        id=invoice.id,
        company_id=invoice.company_id,
        beneficiary_id=invoice.beneficiary_id,
        invoice_number=invoice.invoice_number,
        amount=invoice.amount,
        currency=invoice.currency,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        description=invoice.description,
        status=invoice.status,
        created_at=str(invoice.created_at) if invoice.created_at else None,
        source_type=invoice.source_type,
        file_name=invoice.file_name,
        file_hash=invoice.file_hash,
        file_path=invoice.file_path,
        extraction_confidence=invoice.extraction_confidence,
        raw_text=invoice.raw_text,
        extracted=invoice.extracted,
        ocr_available=extracted.ocr_available,
        ocr_warning=extracted.ocr_warning,
    )


@router.post("/{invoice_id}/extract", tags=["invoices"])
def reextract_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    _user: AppUser = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if not invoice.file_path:
        raise HTTPException(status_code=400, detail="La factura no tiene archivo asociado")

    from pathlib import Path
    path = Path(invoice.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="El archivo subido ya no existe en disco")

    content = path.read_bytes()
    try:
        extracted = extract_file(content, invoice.file_name or "archivo")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _apply_extraction(invoice, extracted, db)
    invoice.raw_text = extracted.raw_text
    invoice.extraction_confidence = extracted.extraction_confidence
    invoice.source_type = extracted.source_type
    db.commit()
    db.refresh(invoice)

    return {
        "invoice_id": invoice.id,
        "source_type": invoice.source_type,
        "raw_text": invoice.raw_text,
        "extraction_confidence": invoice.extraction_confidence,
        "ocr_available": extracted.ocr_available,
        "ocr_warning": extracted.ocr_warning,
    }
