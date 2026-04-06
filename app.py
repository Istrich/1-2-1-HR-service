"""
HR 1-2-1 Web — v2
FastAPI backend: загрузка аудио → транскрипция (Whisper) → аналитический отчёт (GPT)
→ доработка отчёта по комментариям → экспорт в DOCX.
"""

from __future__ import annotations

import os
import re
import uuid
import asyncio
import mimetypes
import logging
import tempfile
import subprocess
import secrets
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta, timezone

import aiohttp
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
    Request,
)
import anyio
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from dotenv import load_dotenv

import jwt as pyjwt

# ====== НАСТРОЙКА ======

ENV_FILE_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_FILE_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hr-121-web")

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
USERS_RAW = os.getenv("USERS", "admin:admin")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

USERS: dict[str, str] = {}
for pair in USERS_RAW.split(","):
    pair = pair.strip()
    if ":" in pair:
        u, p = pair.split(":", 1)
        USERS[u.strip()] = p.strip()

CHUNK_DURATION_SECONDS = 15 * 60
TARGET_SAMPLE_RATE = 16000
TARGET_BITRATE = "64k"
MAX_UPLOAD_MB = 500

OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)


def _safe_output_file(relative: str) -> Path:
    """Путь к файлу в OUTPUTS_DIR без выхода за пределы каталога."""
    base = OUTPUTS_DIR.resolve()
    full = (OUTPUTS_DIR / relative).resolve()
    try:
        full.relative_to(base)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Not found") from e
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return full


def _parse_single_range(range_header: str, size: int) -> tuple[int, int] | None:
    """
    Парсит один диапазон RFC 7233. Возвращает (start, end) включительно или None, если не удовлетворить.
    """
    if size <= 0:
        return None
    if not range_header.startswith("bytes="):
        return None
    spec = range_header[6:].strip()
    if "," in spec:
        return None
    if "-" not in spec:
        return None
    start_s, end_s = spec.split("-", 1)
    try:
        if start_s == "":
            suffix = int(end_s)
            if suffix <= 0:
                return None
            start = max(0, size - suffix)
            end = size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
    except ValueError:
        return None
    if start < 0 or start >= size:
        return None
    end = min(end, size - 1)
    if start > end:
        return None
    return start, end


async def _stream_file_chunks(path: Path, start: int, end: int):
    chunk_size = 64 * 1024
    length = end - start + 1
    async with await anyio.open_file(path, "rb") as f:
        await f.seek(start)
        remaining = length
        while remaining > 0:
            read_n = min(chunk_size, remaining)
            data = await f.read(read_n)
            if not data:
                break
            remaining -= len(data)
            yield data

DEEPSEEK_API_BASE = "https://api.deepseek.com"

_whisper_model = None
_whisper_lock = threading.Lock()
_loaded_whisper_model_name: str | None = None


def reload_dotenv() -> None:
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)


def drop_whisper_model_cache() -> None:
    global _whisper_model, _loaded_whisper_model_name
    with _whisper_lock:
        _whisper_model = None
        _loaded_whisper_model_name = None


def get_whisper_model():
    global _whisper_model, _loaded_whisper_model_name
    name = os.getenv("WHISPER_MODEL", "small").strip()
    with _whisper_lock:
        if _whisper_model is not None and _loaded_whisper_model_name == name:
            return _whisper_model
        import whisper

        logger.info(
            "Loading local Whisper model %r (first run downloads weights; ~18GB RAM: small/medium OK)",
            name,
        )
        _whisper_model = whisper.load_model(name)
        _loaded_whisper_model_name = name
    return _whisper_model


def _escape_env_value(v: str) -> str:
    if re.search(r'[\s#"\'\\]', v) or not v:
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return v


def upsert_env_file(updates: dict[str, str]) -> None:
    """Обновляет или добавляет ключи в .env рядом с app.py (значения не логируем)."""
    path = ENV_FILE_PATH
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    key_to_index: dict[str, int] = {}
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line)
        if m:
            key_to_index[m.group(1)] = i
    for key, value in updates.items():
        new_line = f"{key}={_escape_env_value(value)}"
        if key in key_to_index:
            lines[key_to_index[key]] = new_line
        else:
            lines.append(new_line)
            key_to_index[key] = len(lines) - 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    reload_dotenv()


def get_openai_api_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or "").strip()


def get_deepseek_api_key() -> str:
    return (os.getenv("DEEPSEEK_API_KEY") or "").strip()


def get_report_llm() -> tuple[OpenAI, str]:
    """Клиент и имя модели для отчёта и письма."""
    provider = (os.getenv("REPORT_AI_PROVIDER") or "openai").strip().lower()
    if provider == "deepseek":
        key = get_deepseek_api_key()
        if not key:
            raise ValueError("Не задан ключ DeepSeek (DEEPSEEK_API_KEY). Укажите в настройках «ИИ и API».")
        model = (os.getenv("DEEPSEEK_MODEL") or "deepseek-chat").strip()
        return OpenAI(api_key=key, base_url=DEEPSEEK_API_BASE), model
    key = get_openai_api_key()
    if not key:
        raise ValueError("Не задан ключ OpenAI (OPENAI_API_KEY). Укажите в настройках «ИИ и API».")
    model = (os.getenv("OPENAI_REPORT_MODEL") or "gpt-4o").strip()
    return OpenAI(api_key=key), model


def get_openai_client_for_whisper() -> OpenAI:
    key = get_openai_api_key()
    if not key:
        raise ValueError("Для транскрипции через OpenAI нужен OPENAI_API_KEY.")
    return OpenAI(api_key=key)


def chat_completion(
    client: OpenAI,
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 16000,
) -> str:
    r = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (r.choices[0].message.content or "").strip()


# ====== ПРОМТЫ ======

SYSTEM_REPORT_PROMPT = """
Ты — профессиональный HR-аналитик, специализирующийся на оценке настроений, вовлечённости и рисков сотрудников. 
Твоя задача — сформировать аналитический отчёт по транскрипции 1–2–1 интервью. 

Работай как эксперт-разработчик HR-аналитических заключений: 
- извлекай сигналы и моделируй их последствия;
- не допускай домыслов — разделяй факты (прямые высказывания) и интерпретацию;
- тщательно фиксируй эмоциональные маркеры, формы выражения, силу утверждений;
- классифицируй риски и сложности по типам (процессы, коммуникации, нагрузка, мотивация, конфликт, влияние/позиционирование);
- если сотрудник говорит обтекаемо — так и указывай («обтекаемо выразился...»);
- обязательно используй конкретные цитаты из транскрипции (формат «...» ) и поясняй, какой вывод из них сделан;
- если информации недостаточно — явно указывай это.

Отчёт должен быть детализированным, построен как аналитическое заключение, с чёткой структурой и выводами.
Используй деловой, естественный язык.
Не упрощай формулировки. Стиль — экспертно-аналитический, не реферативный.
"""

DEFAULT_REPORT_PROMPT = """
Проанализируй транскрипцию 1–2–1 интервью ниже и сформируй структурированный аналитический отчёт.

Структура отчёта:

1. Общая информация
   - Дата интервью (если не указана — указать «не указана»)
   - Примерная роль / подразделение
   - Эмоциональный фон (2–3 предложения с указанием конкретных маркеров)

2. Ключевые обсуждённые темы
   - кратко по пунктам

3. Позитивные аспекты / удовлетворённость
   - что оценивается положительно, с указанием цитат

4. Проблемные зоны / сложности
   - классифицировать по типам: процессы / коммуникации / руководитель / нагрузка / мотивация / развитие
   - пояснять по конкретным высказываниям; если вывод косвенный — так и указать

5. Запросы, ожидания, потребности
   - прямые и косвенные сигналы

6. Риски
   - уход, выгорание, конфликт, демотивация
   - обязательно укажи реплики, на которых основан вывод

7. Договорённости и дальнейшие шаги
   - что согласовано, кем, на какой срок (если указано); если нет — «не сформулированы явно»

8. Рекомендации для HR
   - меры по снижению рисков и поддержке мотивации
   - формулируй чётко

Дополнительно:
- Не придумывай факты.
- Чётко разделяй цитаты («…») и интерпретацию.
- Обращай внимание на эмоциональные и смысловые сигналы.
"""

DEFAULT_EMAIL_PROMPT = """
Ты опытный HR-бизнес-партнёр.

На основе транскрипции 1-2-1 встречи с сотрудником сформируй черновик
делового письма для сотрудника, в котором фиксируются результаты и
договорённости встречи.

Требования к письму:
- Стиль: уважительный, конструктивный, деловой, но живой.
- В начале — вежливое приветствие.
- Далее кратко: цель письма и ссылка на прошедшую встречу.
- Затем: ключевые обсуждённые темы, договорённости, шаги, сроки.
- В конце — приглашение уточнить или скорректировать.

Не придумывай новые договорённости. Опирайся только на транскрипцию.
"""

REFINE_SYSTEM_PROMPT = """
Ты — профессиональный HR-аналитик. Тебе дан аналитический отчёт по 1-2-1 интервью
и комментарий от HR-специалиста с просьбой доработать отчёт.

Правила:
- Внеси изменения в отчёт согласно комментарию.
- Сохрани общую структуру и стиль отчёта, если в комментарии не сказано иного.
- Если просят добавить раздел — добавь.
- Если просят убрать — убери.
- Если просят переформулировать — переформулируй.
- Верни полный текст обновлённого отчёта, не только изменённые части.
- Не добавляй служебных комментариев от модели.
"""

# Хранилища per-user
user_prompts: dict[str, dict] = {}
user_sessions: dict[str, dict] = {}


# ====== УТИЛИТЫ АУДИО ======

def run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + args
    subprocess.run(cmd, check=True)


def convert_to_mp3(input_path: Path, output_dir: Path) -> Path:
    output_path = output_dir / f"{uuid.uuid4().hex}.mp3"
    try:
        run_ffmpeg([
            "-i", str(input_path),
            "-ac", "1",
            "-ar", str(TARGET_SAMPLE_RATE),
            "-b:a", TARGET_BITRATE,
            str(output_path),
        ])
    except subprocess.CalledProcessError as e:
        raise ValueError("Не удалось обработать файл — не аудио/видео или повреждён.") from e
    return output_path


def convert_to_playback_mp3(input_path: Path, output_path: Path) -> Path:
    try:
        run_ffmpeg([
            "-i", str(input_path),
            "-ac", "1",
            "-ar", "44100",
            "-b:a", "128k",
            str(output_path),
        ])
    except subprocess.CalledProcessError:
        import shutil
        shutil.copy2(input_path, output_path)
    return output_path


def split_audio_by_time(input_path: Path, output_dir: Path) -> list[Path]:
    pattern = output_dir / (input_path.stem + "_part_%03d.mp3")
    run_ffmpeg([
        "-i", str(input_path),
        "-f", "segment",
        "-segment_time", str(CHUNK_DURATION_SECONDS),
        "-c", "copy",
        str(pattern),
    ])
    parts = sorted(output_dir.glob(input_path.stem + "_part_*.mp3"))
    return parts or [input_path]


def format_hhmmss(total_seconds: float) -> str:
    total_seconds = int(total_seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _get_attr_or_key(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# ====== ТРАНСКРИПЦИЯ ======

def transcribe_chunk(path: Path, language: str = "ru"):
    backend = (os.getenv("WHISPER_BACKEND") or "local").strip().lower()
    if backend in ("api", "openai", "cloud"):
        wclient = get_openai_client_for_whisper()
        with open(path, "rb") as f:
            return wclient.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                language=language,
                timestamp_granularities=["segment"],
            )

    model = get_whisper_model()
    result = model.transcribe(
        str(path),
        language=language,
        fp16=False,
        verbose=False,
    )

    class Seg:
        __slots__ = ("start", "end", "text")

        def __init__(self, start: float, end: float, text: str):
            self.start = start
            self.end = end
            self.text = text

    class Tr:
        __slots__ = ("text", "segments")

    tr = Tr()
    tr.text = (result.get("text") or "").strip()
    segs = []
    for s in result.get("segments") or []:
        if isinstance(s, dict):
            t = (s.get("text") or "").strip()
            st = s.get("start")
            en = s.get("end")
        else:
            t = (_get_attr_or_key(s, "text", "") or "").strip()
            st = _get_attr_or_key(s, "start", None)
            en = _get_attr_or_key(s, "end", None)
        if st is None or en is None:
            continue
        segs.append(Seg(float(st), float(en), t))
    tr.segments = segs
    return tr


def transcribe_full_audio(chunks: list[Path]) -> tuple[str, list[dict]]:
    all_plain_parts: list[str] = []
    all_segments: list[dict] = []

    for idx, chunk in enumerate(chunks, start=1):
        logger.info("Transcribing chunk %d/%d: %s", idx, len(chunks), chunk)
        tr = transcribe_chunk(chunk)

        plain_text = _get_attr_or_key(tr, "text", "") or ""
        if plain_text:
            all_plain_parts.append(plain_text.strip())

        segments = _get_attr_or_key(tr, "segments", []) or []
        chunk_offset_sec = (idx - 1) * CHUNK_DURATION_SECONDS

        for seg in segments:
            seg_start = _get_attr_or_key(seg, "start", None)
            seg_end = _get_attr_or_key(seg, "end", None)
            seg_text = (_get_attr_or_key(seg, "text", "") or "").strip()
            if seg_start is None or seg_end is None or not seg_text:
                continue
            global_start = chunk_offset_sec + float(seg_start)
            global_end = chunk_offset_sec + float(seg_end)
            all_segments.append({
                "start": round(global_start, 2),
                "end": round(global_end, 2),
                "start_fmt": format_hhmmss(global_start),
                "end_fmt": format_hhmmss(global_end),
                "text": seg_text,
            })

    plain_transcript = "\n\n".join(p for p in all_plain_parts if p)

    if not all_segments and plain_transcript:
        all_segments.append({
            "start": 0, "end": 0,
            "start_fmt": "00:00:00", "end_fmt": "",
            "text": plain_transcript,
        })

    return plain_transcript, all_segments


# ====== GPT ======

def build_report(transcript: str, report_prompt: str) -> str:
    llm, model = get_report_llm()
    messages = [
        {"role": "system", "content": SYSTEM_REPORT_PROMPT.strip()},
        {
            "role": "user",
            "content": f"{report_prompt.strip()}\n\n---\n\nТранскрипция:\n\n{transcript}",
        },
    ]
    return chat_completion(llm, model, messages, temperature=0.2)


def refine_report(current_report: str, transcript: str, comment: str) -> str:
    llm, model = get_report_llm()
    messages = [
        {"role": "system", "content": REFINE_SYSTEM_PROMPT.strip()},
        {
            "role": "user",
            "content": (
                f"Транскрипция интервью:\n\n{transcript}\n\n"
                f"---\n\nТекущий отчёт:\n\n{current_report}\n\n"
                f"---\n\nКомментарий от HR-специалиста:\n\n{comment}"
            ),
        },
    ]
    return chat_completion(llm, model, messages, temperature=0.25)


def build_email(transcript: str, email_prompt: str) -> str:
    llm, model = get_report_llm()
    messages = [
        {
            "role": "system",
            "content": email_prompt.strip(),
        },
        {
            "role": "user",
            "content": f"Транскрипция встречи:\n\n{transcript}",
        },
    ]
    return chat_completion(llm, model, messages, temperature=0.3)


# ====== DOCX ======

def build_docx(report_text: str, output_path: Path) -> None:
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    style.font.size = Pt(10.5)
    style.font.color.rgb = RGBColor(0x2D, 0x2D, 0x2D)
    style.paragraph_format.space_after = Pt(4)
    style.paragraph_format.line_spacing = 1.25

    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2)

    title = doc.add_heading("Аналитический отчёт по 1-2-1 интервью", level=1)
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = meta.add_run(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x6B, 0x6B, 0x6B)
    run.font.italic = True
    doc.add_paragraph("")

    def add_md_paragraph(text: str, style_name: str | None = None):
        p = doc.add_paragraph(style=style_name) if style_name else doc.add_paragraph()
        parts = re.split(r"(\*\*[^*]+\*\*)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                p.add_run(part[2:-2]).bold = True
            else:
                p.add_run(part)
        return p

    lines = report_text.splitlines()
    n = len(lines)

    for idx, line in enumerate(lines):
        stripped = line.strip()
        next_stripped = lines[idx + 1].strip() if idx + 1 < n else ""

        if not stripped:
            continue
        if re.fullmatch(r"[-*_]{3,}", stripped):
            continue
        if stripped.startswith("### "):
            h = doc.add_heading(stripped[4:], level=3)
            for r in h.runs:
                r.font.color.rgb = RGBColor(0x33, 0x33, 0x50)
                r.font.size = Pt(11)
            continue
        if stripped.startswith("## "):
            h = doc.add_heading(stripped[3:], level=2)
            for r in h.runs:
                r.font.color.rgb = RGBColor(0x2A, 0x2A, 0x45)
                r.font.size = Pt(12.5)
            continue
        if stripped.startswith("# "):
            h = doc.add_heading(stripped[2:], level=2)
            for r in h.runs:
                r.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
                r.font.size = Pt(14)
            continue

        m_section = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if m_section:
            if not next_stripped or next_stripped.startswith(("- ", "• ")):
                h = doc.add_heading(stripped, level=2)
                for r in h.runs:
                    r.font.color.rgb = RGBColor(0x2A, 0x2A, 0x45)
                    r.font.size = Pt(12.5)
                continue

        if (stripped.startswith("«") and stripped.endswith("»")) or stripped.startswith("> "):
            text = stripped.lstrip("> ").strip()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1)
            run = p.add_run(text)
            run.italic = True
            run.font.color.rgb = RGBColor(0x55, 0x55, 0x70)
            continue

        if stripped.startswith("- "):
            add_md_paragraph(stripped[2:], style_name="List Bullet")
            continue
        if stripped.startswith("• "):
            add_md_paragraph(stripped[2:].lstrip(), style_name="List Bullet")
            continue

        add_md_paragraph(stripped)

    doc.save(output_path)


# ====== URL ======

def normalize_url(url: str) -> str:
    m = re.search(r"drive\.google\.com/file/d/([^/]+)/", url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r"drive\.google\.com/.*?[?&]id=([^&]+)", url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    if "dropbox.com" in url:
        if "dl=" in url:
            url = re.sub(r"dl=\d", "dl=1", url)
        else:
            url = f"{url}{'&' if '?' in url else '?'}dl=1"
        m = re.search(r"www\.dropbox.com/s/([^/]+)/([^?]+)", url)
        if m:
            return f"https://dl.dropboxusercontent.com/s/{m.group(1)}/{m.group(2)}"
    return url


async def download_url_to_temp(url: str, tmpdir: Path) -> Path:
    normalized = normalize_url(url)
    dest_path = tmpdir / uuid.uuid4().hex
    async with aiohttp.ClientSession() as session:
        async with session.get(normalized) as resp:
            if resp.status != 200:
                raise ValueError(f"Не удалось скачать (HTTP {resp.status}).")
            ct = resp.headers.get("Content-Type", "").lower()
            if "text/html" in ct:
                raise ValueError("По ссылке — веб-страница, а не файл.")
            first = await resp.content.read(4096)
            s = first.lstrip().lower()
            if s.startswith(b"<!doctype html") or s.startswith(b"<html"):
                raise ValueError("По ссылке загружается HTML.")
            with open(dest_path, "wb") as f:
                f.write(first)
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    f.write(chunk)
    return dest_path


# ====== JWT ======

def create_token(username: str) -> str:
    return pyjwt.encode(
        {"sub": username, "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)},
        SECRET_KEY, algorithm=JWT_ALGORITHM,
    )

def verify_token(token: str) -> str | None:
    try:
        return pyjwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM]).get("sub")
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None

async def get_current_user(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401)
    username = verify_token(auth[7:])
    if not username:
        raise HTTPException(status_code=401)
    return username


# ====== APP ======

app = FastAPI(title="HR 1-2-1 Web")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.api_route("/outputs/{path:path}", methods=["GET", "HEAD"])
async def serve_outputs_file(path: str, request: Request):
    """
    Отдача файлов из outputs/ с поддержкой HTTP Range (нужно для перемотки <audio> в браузере).
    Обычный StaticFiles/FileResponse в Starlette отдаёт файл целиком без 206 Partial Content.
    """
    full = _safe_output_file(path)
    stat = full.stat()
    size = stat.st_size
    media_type, _ = mimetypes.guess_type(str(full))
    if not media_type:
        media_type = "application/octet-stream"

    range_header = request.headers.get("range")
    common_headers: dict[str, str] = {"accept-ranges": "bytes"}

    if size == 0:
        if request.method == "HEAD":
            return Response(status_code=200, headers={**common_headers, "content-length": "0"}, media_type=media_type)
        return Response(content=b"", status_code=200, headers={**common_headers, "content-length": "0"}, media_type=media_type)

    if range_header:
        parsed = _parse_single_range(range_header, size)
        if parsed is None:
            return Response(
                status_code=416,
                headers={**common_headers, "content-range": f"bytes */{size}"},
                media_type=media_type,
            )
        start, end = parsed
        chunk_len = end - start + 1
        headers = {
            **common_headers,
            "content-range": f"bytes {start}-{end}/{size}",
            "content-length": str(chunk_len),
        }
        if request.method == "HEAD":
            return Response(status_code=206, headers=headers, media_type=media_type)
        return StreamingResponse(
            _stream_file_chunks(full, start, end),
            status_code=206,
            media_type=media_type,
            headers=headers,
        )

    headers = {**common_headers, "content-length": str(size)}
    if request.method == "HEAD":
        return Response(status_code=200, headers=headers, media_type=media_type)
    return StreamingResponse(
        _stream_file_chunks(full, 0, size - 1),
        status_code=200,
        media_type=media_type,
        headers=headers,
    )


class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/login")
async def login(req: LoginRequest):
    if req.username not in USERS or USERS[req.username] != req.password:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return {"token": create_token(req.username), "username": req.username}

@app.get("/api/me")
async def me(user: str = Depends(get_current_user)):
    return {"username": user}


def _get_user_prompts(user: str) -> dict:
    if user not in user_prompts:
        user_prompts[user] = {"report": DEFAULT_REPORT_PROMPT, "email": DEFAULT_EMAIL_PROMPT}
    return user_prompts[user]

@app.get("/api/prompts")
async def get_prompts(user: str = Depends(get_current_user)):
    p = _get_user_prompts(user)
    return {
        "report_prompt": p["report"], "email_prompt": p["email"],
        "default_report_prompt": DEFAULT_REPORT_PROMPT,
        "default_email_prompt": DEFAULT_EMAIL_PROMPT,
    }

class PromptUpdate(BaseModel):
    prompt_type: str
    text: str

@app.post("/api/prompts")
async def update_prompt(req: PromptUpdate, user: str = Depends(get_current_user)):
    if req.prompt_type not in ("report", "email"):
        raise HTTPException(status_code=400)
    _get_user_prompts(user)[req.prompt_type] = req.text
    return {"ok": True}

@app.post("/api/prompts/reset")
async def reset_prompt(req: PromptUpdate, user: str = Depends(get_current_user)):
    p = _get_user_prompts(user)
    p[req.prompt_type] = {"report": DEFAULT_REPORT_PROMPT, "email": DEFAULT_EMAIL_PROMPT}.get(req.prompt_type, "")
    return {"ok": True}


# --- Runtime / .env (ИИ и транскрипция) ---


class RuntimeSettingsUpdate(BaseModel):
    report_ai_provider: Optional[str] = None
    whisper_backend: Optional[str] = None
    whisper_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None


@app.get("/api/settings/runtime")
async def get_runtime_settings(user: str = Depends(get_current_user)):
    return {
        "report_ai_provider": (os.getenv("REPORT_AI_PROVIDER") or "openai").strip().lower(),
        "whisper_backend": (os.getenv("WHISPER_BACKEND") or "local").strip().lower(),
        "whisper_model": (os.getenv("WHISPER_MODEL") or "small").strip(),
        "openai_key_set": bool(get_openai_api_key()),
        "deepseek_key_set": bool(get_deepseek_api_key()),
    }


@app.post("/api/settings/runtime")
async def save_runtime_settings(req: RuntimeSettingsUpdate, user: str = Depends(get_current_user)):
    old_wm = (os.getenv("WHISPER_MODEL") or "small").strip()
    old_wb = (os.getenv("WHISPER_BACKEND") or "local").strip().lower()
    updates: dict[str, str] = {}
    if req.report_ai_provider is not None:
        p = req.report_ai_provider.strip().lower()
        if p not in ("openai", "deepseek"):
            raise HTTPException(status_code=400, detail="report_ai_provider: openai или deepseek")
        updates["REPORT_AI_PROVIDER"] = p
    if req.whisper_backend is not None:
        b = req.whisper_backend.strip().lower()
        if b not in ("local", "api"):
            raise HTTPException(status_code=400, detail="whisper_backend: local или api")
        updates["WHISPER_BACKEND"] = b
    if req.whisper_model is not None:
        updates["WHISPER_MODEL"] = req.whisper_model.strip()
    if req.openai_api_key is not None:
        k = req.openai_api_key.strip()
        if k:
            updates["OPENAI_API_KEY"] = k
    if req.deepseek_api_key is not None:
        k = req.deepseek_api_key.strip()
        if k:
            updates["DEEPSEEK_API_KEY"] = k
    if updates:
        upsert_env_file(updates)
        new_wm = (os.getenv("WHISPER_MODEL") or "small").strip()
        new_wb = (os.getenv("WHISPER_BACKEND") or "local").strip().lower()
        if old_wm != new_wm or old_wb != new_wb:
            drop_whisper_model_cache()
    return {"ok": True}


# --- Core processing ---

async def _process_audio_file(input_path: Path, user: str) -> dict:
    prompts = _get_user_prompts(user)
    session_id = uuid.uuid4().hex[:12]

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        converted = await asyncio.to_thread(convert_to_mp3, input_path, tmpdir)
        chunks = await asyncio.to_thread(split_audio_by_time, converted, tmpdir)
        plain_transcript, segments = await asyncio.to_thread(transcribe_full_audio, chunks)

        audio_filename = f"{session_id}_audio.mp3"
        await asyncio.to_thread(convert_to_playback_mp3, input_path, OUTPUTS_DIR / audio_filename)

        report_text = await asyncio.to_thread(build_report, plain_transcript, prompts["report"])

    user_sessions[user] = {
        "session_id": session_id,
        "transcript": plain_transcript,
        "segments": segments,
        "report": report_text,
        "audio_file": f"/outputs/{audio_filename}",
    }

    return {
        "session_id": session_id,
        "segments": segments,
        "report": report_text,
        "audio_file": f"/outputs/{audio_filename}",
    }


@app.post("/api/process/upload")
async def process_upload(file: UploadFile = File(...), user: str = Depends(get_current_user)):
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        input_path = tmpdir / (file.filename or f"{uuid.uuid4().hex}.audio")
        content = await file.read()
        if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"Макс. {MAX_UPLOAD_MB} МБ")
        with open(input_path, "wb") as f:
            f.write(content)
        try:
            return await _process_audio_file(input_path, user)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/process/url")
async def process_url(url: str = Form(...), user: str = Depends(get_current_user)):
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        try:
            input_path = await download_url_to_temp(url, tmpdir)
            return await _process_audio_file(input_path, user)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e


class RefineRequest(BaseModel):
    comment: str
    current_report: str

@app.post("/api/refine")
async def refine_report_endpoint(req: RefineRequest, user: str = Depends(get_current_user)):
    session = user_sessions.get(user)
    if not session:
        raise HTTPException(status_code=404, detail="Нет активной сессии")
    try:
        refined = await asyncio.to_thread(refine_report, req.current_report, session["transcript"], req.comment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    session["report"] = refined
    return {"report": refined}


@app.post("/api/email")
async def generate_email(user: str = Depends(get_current_user)):
    session = user_sessions.get(user)
    if not session:
        raise HTTPException(status_code=404, detail="Нет активной сессии")
    prompts = _get_user_prompts(user)
    try:
        email_text = await asyncio.to_thread(build_email, session["transcript"], prompts["email"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"email_text": email_text}


class ExportRequest(BaseModel):
    report_text: str

@app.post("/api/export/docx")
async def export_docx(req: ExportRequest, user: str = Depends(get_current_user)):
    session = user_sessions.get(user)
    sid = session["session_id"] if session else uuid.uuid4().hex[:12]
    filename = f"{sid}_report.docx"
    await asyncio.to_thread(build_docx, req.report_text, OUTPUTS_DIR / filename)
    return {"file": f"/outputs/{filename}"}


@app.get("/")
async def index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
