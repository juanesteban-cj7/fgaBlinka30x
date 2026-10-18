from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.agreement import Agreement
from app.models.app_user import AppUser
from app.models.beneficiary import Beneficiary
from app.models.invoice import Invoice
from app.rules.normalization import norm_name
from app.schemas.beneficiary import BeneficiaryOut, BeneficiaryCreate, BeneficiaryUpdate

router = APIRouter()


@router.get("/", response_model=list[BeneficiaryOut], tags=["beneficiaries"])
def list_beneficiaries(company_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Beneficiary)
    if company_id:
        query = query.filter(Beneficiary.company_id == company_id)
    return query.order_by(Beneficiary.name).all()


@router.post("/", response_model=BeneficiaryOut, status_code=201, tags=["beneficiaries"])
def create_beneficiary(
    payload: BeneficiaryCreate,
    db: Session = Depends(get_db),
    _user: AppUser = Depends(get_current_user),
):
    existing = (
        db.query(Beneficiary)
        .filter(Beneficiary.id == payload.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="El beneficiario ya existe")
    beneficiary_data = payload.model_dump()
    beneficiary_data["normalized_name"] = norm_name(
        beneficiary_data["name"]
    )
    beneficiary = Beneficiary(**beneficiary_data)
    db.add(beneficiary)
    db.commit()
    db.refresh(beneficiary)
    return beneficiary


@router.patch("/{beneficiary_id}", response_model=BeneficiaryOut, tags=["beneficiaries"])
def update_beneficiary(
    beneficiary_id: str,
    payload: BeneficiaryUpdate,
    db: Session = Depends(get_db),
    _user: AppUser = Depends(get_current_user),
):
    beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id).first()
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiario no encontrado")

    update_values = payload.model_dump(exclude_unset=True)
    if "name" in update_values and update_values["name"] is not None:
        name = update_values["name"].strip()
        if not name:
            raise HTTPException(status_code=422, detail="El nombre no puede estar vacío")
        update_values["name"] = name
        beneficiary.name = name
        beneficiary.normalized_name = norm_name(name)
    for field in ("allowed", "reference_code", "category"):
        if field in update_values:
            setattr(beneficiary, field, update_values[field])

    db.commit()
    db.refresh(beneficiary)
    return beneficiary


@router.delete("/{beneficiary_id}", status_code=204, tags=["beneficiaries"])
def delete_beneficiary(
    beneficiary_id: str,
    db: Session = Depends(get_db),
    _user: AppUser = Depends(get_current_user),
):
    beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id).first()
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiario no encontrado")

    has_invoices = db.query(Invoice.id).filter(
        Invoice.beneficiary_id == beneficiary.id
    ).first()
    has_agreements = db.query(Agreement.id).filter(
        Agreement.beneficiary_id == beneficiary.id
    ).first()
    if has_invoices or has_agreements:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar el beneficiario porque tiene facturas o acuerdos asociados.",
        )

    db.delete(beneficiary)
    db.commit()
