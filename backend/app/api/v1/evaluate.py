from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.deps import DemoActor, get_demo_actor
from app.database import get_db
from app.models.invoice import Invoice
from app.models.decision_record import DecisionRecord
from app.schemas.evaluation import EvaluationResult
from app.services.evaluation import evaluate_and_record

router = APIRouter()


@router.post("/{invoice_id}/evaluate", response_model=EvaluationResult, tags=["invoices"])
def evaluate_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    user: DemoActor = Depends(get_demo_actor),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return evaluate_and_record(db, invoice_id, actor=user)


@router.get("/{invoice_id}/decisions", tags=["invoices"])
def list_decisions(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    decisions = (
        db.query(DecisionRecord)
        .filter(DecisionRecord.invoice_id == invoice_id)
        .order_by(DecisionRecord.created_at.desc())
        .all()
    )
    return decisions
