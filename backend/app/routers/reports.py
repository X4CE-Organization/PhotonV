"""举报：用户提交与查看自己的举报。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..security import require_user
from ..utils import audit, fail, iso, rate_limit

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("")
def create_report(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    if not site.get_bool("allow_report", True):
        raise fail(403, "本站已关闭举报功能")
    if not rate_limit(f"report:{user.id}", 60):
        raise fail(429, "举报提交过于频繁，请稍后再试")

    target_type = str(payload.get("target_type") or "")
    if target_type not in {"video", "comment", "user", "danmaku"}:
        raise fail(400, "举报对象不合法")
    target_id = int(payload.get("target_id") or 0)
    if not target_id:
        raise fail(400, "缺少举报对象")

    reasons = [item["value"] for item in (site.get_json("report_reasons", []) or [])]
    reason = str(payload.get("reason") or "other")
    if reasons and reason not in reasons:
        reason = "other"

    report = models.Report(
        reporter_id=user.id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        detail=str(payload.get("detail") or "")[:1000],
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    audit(db, request, user, "report.create", target_type, target_id, reason)
    return {"ok": True, "id": report.id}


@router.get("/mine")
def my_reports(db: Session = Depends(get_db), user: models.User = Depends(require_user)):
    rows = db.scalars(
        select(models.Report).where(models.Report.reporter_id == user.id).order_by(models.Report.id.desc()).limit(50)
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "targetType": item.target_type,
                "targetId": item.target_id,
                "reason": item.reason,
                "detail": item.detail,
                "status": item.status,
                "handleNote": item.handle_note,
                "createdAt": iso(item.created_at),
                "handledAt": iso(item.handled_at),
            }
            for item in rows
        ]
    }
