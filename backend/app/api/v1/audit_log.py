from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.app_user import AppUser
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogPage

router = APIRouter()


@router.get("/", response_model=AuditLogPage, tags=["audit-log"])
def list_audit_log(
    action: list[str] | None = Query(default=None),
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: AppUser = Depends(get_current_user),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.in_(action))
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if date_from:
        query = query.filter(
            AuditLog.created_at >= datetime.combine(date_from, time.min)
        )
    if date_to:
        query = query.filter(
            AuditLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )
    if q and q.strip():
        query = query.filter(AuditLog.summary.ilike(f"%{q.strip()}%"))

    total = query.with_entities(func.count(AuditLog.id)).scalar() or 0
    items = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return AuditLogPage(items=items, total=total)
