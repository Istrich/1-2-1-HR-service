from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from pydantic import BaseModel
from app.core.security import get_current_user
from app.db.database import AsyncSessionLocal
from app.db.models import Report

router = APIRouter()

@router.get("/reports")
async def list_reports(user: str = Depends(get_current_user), q: str = ""):
    async with AsyncSessionLocal() as session:
        query = select(Report).where(Report.user == user).order_by(Report.created_at.desc())
        result = await session.execute(query)
        reports = result.scalars().all()

        items = []
        qn = (q or "").strip().lower()
        for r in reports:
            title = r.title or "Без названия"
            if qn and qn not in title.lower():
                continue
            items.append({
                "id": r.id,
                "title": title,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "audio_bytes": r.audio_bytes or 0,
                "audio_file": f"/outputs/{r.audio_file}" if r.audio_file else None,
            })
        return {"items": items}

class ReportPatch(BaseModel):
    title: str | None = None
    report: str | None = None

@router.get("/reports/{report_id}")
async def get_report(report_id: str, user: str = Depends(get_current_user)):
    import json
    from app.core.config import OUTPUTS_DIR

    async with AsyncSessionLocal() as session:
        r = await session.get(Report, report_id)
        if not r or r.user != user:
            raise HTTPException(status_code=404, detail="Не найдено")

    tf = r.transcript_file
    rf = r.report_file
    af = r.audio_file

    tp = OUTPUTS_DIR / tf
    rp = OUTPUTS_DIR / rf

    if not tp.is_file() or not rp.is_file():
        raise HTTPException(status_code=404, detail="Файлы отчёта отсутствуют")

    traw = tp.read_text(encoding="utf-8")
    report_text = rp.read_text(encoding="utf-8")

    try:
        tdata = json.loads(traw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Повреждён файл транскрипции")

    plain = (tdata.get("transcript") or "").strip() if isinstance(tdata, dict) else ""
    segments = tdata.get("segments") if isinstance(tdata, dict) else []
    audio_url = f"/outputs/{af}"

    # Also we are requested to keep 'user_sessions' logic per user for refine/email.
    # For now, let's keep it in memory in this module
    USER_SESSIONS[user] = {
        "session_id": r.id,
        "transcript": plain,
        "report": report_text,
    }

    return {
        "session_id": r.id,
        "report_id": r.id,
        "title": r.title,
        "audio_bytes": r.audio_bytes,
        "segments": segments,
        "report": report_text,
        "audio_file": audio_url,
    }

USER_SESSIONS: dict[str, dict] = {}

@router.patch("/reports/{report_id}")
async def patch_report(report_id: str, req: ReportPatch, user: str = Depends(get_current_user)):
    from app.core.config import OUTPUTS_DIR
    async with AsyncSessionLocal() as session:
        r = await session.get(Report, report_id)
        if not r or r.user != user:
            raise HTTPException(status_code=404, detail="Не найдено")

        if req.title is not None:
            r.title = req.title.strip()

        if req.report is not None:
            rf = r.report_file
            if rf:
                rp = OUTPUTS_DIR / rf
                rp.write_text(req.report, encoding="utf-8")

        await session.commit()
    return {"ok": True}

@router.delete("/reports/{report_id}")
async def delete_report(report_id: str, user: str = Depends(get_current_user)):
    from app.core.config import OUTPUTS_DIR
    async with AsyncSessionLocal() as session:
        r = await session.get(Report, report_id)
        if not r or r.user != user:
            raise HTTPException(status_code=404, detail="Не найдено")

        # Delete files
        for n in [r.audio_file, r.transcript_file, r.report_file, f"{report_id}_report.docx"]:
            if n:
                p = OUTPUTS_DIR / n
                if p.is_file():
                    p.unlink(missing_ok=True)

        await session.delete(r)
        await session.commit()
    return {"ok": True}

class RefineRequest(BaseModel):
    comment: str
    current_report: str

@router.post("/refine")
async def refine_report_endpoint(req: RefineRequest, user: str = Depends(get_current_user)):
    import asyncio
    from app.services.llm import refine_report
    from app.core.config import OUTPUTS_DIR

    session = USER_SESSIONS.get(user)
    if not session:
        raise HTTPException(status_code=404, detail="Нет активной сессии")

    refined = await asyncio.to_thread(refine_report, req.current_report, session["transcript"], req.comment)
    session["report"] = refined

    # Save to disk
    async with AsyncSessionLocal() as db_session:
        r = await db_session.get(Report, session["session_id"])
        if r and r.report_file:
            rp = OUTPUTS_DIR / r.report_file
            rp.write_text(refined, encoding="utf-8")

    return {"report": refined}

@router.post("/email")
async def generate_email(user: str = Depends(get_current_user)):
    import asyncio
    from app.services.llm import build_email
    from app.api.endpoints.settings import _get_user_prompts

    session = USER_SESSIONS.get(user)
    if not session:
        raise HTTPException(status_code=404, detail="Нет активной сессии")

    prompts = _get_user_prompts(user)
    email_text = await asyncio.to_thread(build_email, session["transcript"], prompts["email"])
    return {"email_text": email_text}

class ExportRequest(BaseModel):
    report_text: str

@router.post("/export/docx")
async def export_docx(req: ExportRequest, user: str = Depends(get_current_user)):
    import asyncio
    import uuid
    from app.services.docx import build_docx
    from app.core.config import OUTPUTS_DIR

    session = USER_SESSIONS.get(user)
    sid = session["session_id"] if session else uuid.uuid4().hex[:12]
    filename = f"{sid}_report.docx"

    await asyncio.to_thread(build_docx, req.report_text, OUTPUTS_DIR / filename)
    return {"file": f"/outputs/{filename}"}
