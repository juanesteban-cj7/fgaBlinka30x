from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogEntry(BaseModel):
    id: str
    created_at: datetime
    actor_type: str
    actor_id: str | None
    actor_name: str
    action: str
    entity_type: str
    entity_id: str
    entity_label: str
    company_id: str | None
    summary: str
    changes: dict[str, Any] | None
    metadata: dict[str, Any] | None = Field(validation_alias="event_metadata")

    model_config = ConfigDict(from_attributes=True)


class AuditLogPage(BaseModel):
    items: list[AuditLogEntry]
    total: int
