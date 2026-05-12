import os
import uuid
import tempfile
import asyncio
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from app.core.security import get_current_user
from app.services.task_runner import start_processing_task, get_task_status, subscribe_to_task
from app.services.audio import convert_to_mp3, split_audio_by_time, convert_to_playback_mp3
from app.services.transcription import transcribe_full_audio
from app.services.llm import build_report, DEFAULT_REPORT_PROMPT
from app.core.config import MAX_UPLOAD_MB

router = APIRouter()

PROCESS_FUNCS = {
    "convert_to_mp3": convert_to_mp3,
    "split_audio_by_time": split_audio_by_time,
    "convert_to_playback_mp3": convert_to_playback_mp3,
    "transcribe_full_audio": transcribe_full_audio,
    "build_report": build_report,
}

@router.post("/process/upload")
async def process_upload(file: UploadFile = File(...), user: str = Depends(get_current_user)):
    orig_name = file.filename or f"upload_{uuid.uuid4().hex[:8]}"
    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Макс. {MAX_UPLOAD_MB} МБ")

    # Needs to persist until task finishes
    tmpdir = Path(tempfile.gettempdir())
    input_path = tmpdir / f"{uuid.uuid4().hex}_{orig_name}"
    with open(input_path, "wb") as f:
        f.write(content)

    report_prompt = DEFAULT_REPORT_PROMPT # In real app, fetch from DB

    task_id = start_processing_task(input_path, user, orig_name, report_prompt, PROCESS_FUNCS)
    return {"task_id": task_id}

@router.post("/process/url")
async def process_url(url: str = Form(...), user: str = Depends(get_current_user)):
    from app.services.download import download_url_to_temp
    tmpdir = Path(tempfile.gettempdir())
    try:
        input_path = await download_url_to_temp(url, tmpdir)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    report_prompt = DEFAULT_REPORT_PROMPT
    task_id = start_processing_task(input_path, user, "url_download", report_prompt, PROCESS_FUNCS)
    return {"task_id": task_id}

@router.get("/process/status/{task_id}")
async def get_status(task_id: str, req: Request, user: str = Depends(get_current_user)):
    status = get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        # First yield current status
        import json
        yield {"data": json.dumps(status)}

        # Subscribe for future updates
        q = await subscribe_to_task(task_id)
        try:
            while True:
                if await req.is_disconnected():
                    break
                data = await q.get()
                yield {"data": data}
                state = json.loads(data)
                if state["status"] in ("done", "error"):
                    break
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())
