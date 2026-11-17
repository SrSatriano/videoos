from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ScheduleSlot, PublishTask
from ..schemas import CalendarBuildRequest
from ..serializers import schedule_slot_to_dict
from ..services.calendar import build_schedule

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.post("/build")
def build(payload: CalendarBuildRequest):
    slots = build_schedule(payload.start_at, payload.count, payload.interval_minutes, payload.platforms)
    return {
        "slots": [
            {
                **slot,
                "publish_at": slot["publish_at"].isoformat(),
            }
            for slot in slots
        ]
    }


@router.get("/slots")
def list_calendar_slots(db: Session = Depends(get_db)):
    slots = db.query(ScheduleSlot).order_by(ScheduleSlot.publish_at.asc()).all()
    result: list[dict[str, Any]] = []
    for slot in slots:
        data = schedule_slot_to_dict(slot)
        if slot.publish_task_id:
            task = db.get(PublishTask, slot.publish_task_id)
            if task:
                data["package_dir"] = task.package_dir
                data["caption"] = task.caption
        result.append(data)
    return result


@router.post("/slots")
def create_calendar_slot(payload: dict, db: Session = Depends(get_db)):
    publish_at_raw = payload.get("publish_at")
    if not publish_at_raw:
        raise HTTPException(status_code=422, detail="publish_at obrigatorio.")
    publish_at = datetime.fromisoformat(publish_at_raw.replace("Z", "+00:00"))
    slot = ScheduleSlot(
        platform=payload.get("platform", "instagram_reels"),
        publish_at=publish_at,
        publish_task_id=payload.get("publish_task_id"),
        status=payload.get("status", "planned" if not payload.get("publish_task_id") else "ready"),
        notes=payload.get("notes", ""),
        order_index=int(payload.get("order_index", 1)),
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return schedule_slot_to_dict(slot)


@router.post("/generate-week")
def generate_weekly_slots(payload: dict | None = None, db: Session = Depends(get_db)):
    """Gera grade semanal de slots nos horários nobres de engajamento (12:00 e 18:30)."""
    now = datetime.utcnow()
    platforms = (payload or {}).get("platforms", ["instagram_reels", "tiktok", "youtube_shorts"])
    created_slots = []
    for day in range(7):
        target_date = now + timedelta(days=day)
        slot_times = [
            target_date.replace(hour=12, minute=0, second=0, microsecond=0),
            target_date.replace(hour=18, minute=30, second=0, microsecond=0),
        ]
        for idx, slot_time in enumerate(slot_times):
            platform = platforms[(day + idx) % len(platforms)]
            slot = ScheduleSlot(
                platform=platform,
                publish_at=slot_time,
                status="planned",
                notes=f"Slot automatico dia +{day} ({slot_time.strftime('%H:%M')})",
                order_index=day * 2 + idx + 1,
            )
            db.add(slot)
            created_slots.append(slot)
    db.commit()
    return {"created": len(created_slots), "slots": [schedule_slot_to_dict(s) for s in created_slots]}


@router.patch("/slots/{slot_id}")
def update_calendar_slot(slot_id: str, payload: dict, db: Session = Depends(get_db)):
    slot = db.get(ScheduleSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot de agendamento nao encontrado.")
    if "status" in payload:
        slot.status = str(payload["status"])
    if "notes" in payload:
        slot.notes = str(payload["notes"])
    if "publish_at" in payload and payload["publish_at"]:
        slot.publish_at = datetime.fromisoformat(str(payload["publish_at"]).replace("Z", "+00:00"))
    if "publish_task_id" in payload:
        slot.publish_task_id = payload["publish_task_id"]
    db.commit()
    db.refresh(slot)
    return schedule_slot_to_dict(slot)


@router.delete("/slots/{slot_id}")
def delete_calendar_slot(slot_id: str, db: Session = Depends(get_db)):
    slot = db.get(ScheduleSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot nao encontrado.")
    db.delete(slot)
    db.commit()
    return {"status": "deleted", "id": slot_id}

