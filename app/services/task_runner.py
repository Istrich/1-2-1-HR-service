import asyncio
import uuid
import json
import logging
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any, Callable
from app.core.config import OUTPUTS_DIR
from app.db.database import AsyncSessionLocal
from app.db.models import Report

logger = logging.getLogger(__name__)

# Basic in-memory task status storage
# Structure: task_id -> {"status": str, "result": dict|None, "error": str|None, "progress": int}
TASKS: Dict[str, Dict[str, Any]] = {}
# Subscribers for SSE: task_id -> list of AsyncQueue
TASK_SUBSCRIBERS: Dict[str, list[asyncio.Queue]] = {}

def get_task_status(task_id: str):
    return TASKS.get(task_id)

async def _notify_subscribers(task_id: str):
    if task_id in TASK_SUBSCRIBERS:
        state = TASKS.get(task_id)
        if not state: return
        data = json.dumps(state)
        for q in TASK_SUBSCRIBERS[task_id]:
            await q.put(data)

def _update_task(task_id: str, **kwargs):
    if task_id in TASKS:
        TASKS[task_id].update(kwargs)
        asyncio.create_task(_notify_subscribers(task_id))

async def process_audio_file_task(
    task_id: str,
    input_path: Path,
    user: str,
    source_name: str,
    report_prompt: str,
    process_funcs: dict
):
    """
    Background task to process audio, transcribe, and generate a report.
    """
    session_id = uuid.uuid4().hex[:12]
    now_str = datetime.now().strftime('%d.%m.%Y %H:%M')
    title = source_name[:117] + "..." if len(source_name) > 120 else source_name
    if not title: title = f"Отчёт {now_str}"

    try:
        _update_task(task_id, status="converting", progress=10)
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)

            # Step 1: Convert to generic MP3 and Split
            converted = await asyncio.to_thread(process_funcs['convert_to_mp3'], input_path, tmpdir)
            chunks = await asyncio.to_thread(process_funcs['split_audio_by_time'], converted, tmpdir)

            # Create playback MP3 (needs to be available for web player)
            audio_filename = f"{session_id}_audio.mp3"
            playback_path = OUTPUTS_DIR / audio_filename
            await asyncio.to_thread(process_funcs['convert_to_playback_mp3'], input_path, playback_path)

            _update_task(task_id, status="transcribing", progress=40)

            # Step 2: Transcribe chunks
            plain_transcript, segments = await asyncio.to_thread(process_funcs['transcribe_full_audio'], chunks)

            _update_task(task_id, status="generating_report", progress=75)

            # Step 3: Build Report
            report_text = await asyncio.to_thread(process_funcs['build_report'], plain_transcript, report_prompt)

            # Step 4: Save outputs
            _update_task(task_id, status="saving", progress=90)

            audio_bytes = playback_path.stat().st_size
            transcript_filename = f"{session_id}_transcript.json"
            report_filename = f"{session_id}_report.md"

            tjson = json.dumps({"transcript": plain_transcript, "segments": segments}, ensure_ascii=False)
            tp = OUTPUTS_DIR / transcript_filename
            rp = OUTPUTS_DIR / report_filename

            def _write_reports():
                tp.write_text(tjson, encoding="utf-8")
                rp.write_text(report_text, encoding="utf-8")
            await asyncio.to_thread(_write_reports)

            # Step 5: Save DB Record
            async with AsyncSessionLocal() as session:
                new_report = Report(
                    id=session_id,
                    user=user,
                    title=title,
                    audio_file=audio_filename,
                    audio_bytes=audio_bytes,
                    transcript_file=transcript_filename,
                    report_file=report_filename
                )
                session.add(new_report)
                await session.commit()

            result_data = {
                "session_id": session_id,
                "report_id": session_id,
                "title": title,
                "audio_bytes": audio_bytes,
                "segments": segments,
                "report": report_text,
                "audio_file": f"/outputs/{audio_filename}"
            }

            from app.api.endpoints.reports import USER_SESSIONS
            USER_SESSIONS[user] = {
                "session_id": session_id,
                "transcript": plain_transcript,
                "report": report_text,
            }

            _update_task(task_id, status="done", progress=100, result=result_data)

    except Exception as e:
        logger.exception(f"Error processing task {task_id}")
        _update_task(task_id, status="error", error=str(e))
    finally:
        # Cleanup input file
        if input_path.exists():
            input_path.unlink()

        # Cleanup subscribers after a short delay
        async def _cleanup():
            await asyncio.sleep(60)
            TASKS.pop(task_id, None)
            TASK_SUBSCRIBERS.pop(task_id, None)
        asyncio.create_task(_cleanup())

def start_processing_task(input_path: Path, user: str, source_name: str, report_prompt: str, process_funcs: dict) -> str:
    task_id = uuid.uuid4().hex
    TASKS[task_id] = {"status": "pending", "progress": 0, "result": None, "error": None}
    TASK_SUBSCRIBERS[task_id] = []

    asyncio.create_task(process_audio_file_task(task_id, input_path, user, source_name, report_prompt, process_funcs))
    return task_id

async def subscribe_to_task(task_id: str):
    q = asyncio.Queue()
    if task_id not in TASK_SUBSCRIBERS:
        TASK_SUBSCRIBERS[task_id] = []
    TASK_SUBSCRIBERS[task_id].append(q)
    return q
