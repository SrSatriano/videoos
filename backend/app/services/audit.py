from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import AuditEvent


def record_event(
    db: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        message=message,
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
