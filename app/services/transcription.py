import os
import threading
import time
import logging
from pathlib import Path
from openai import OpenAI, APIError
from app.core.config import CHUNK_DURATION_SECONDS
from app.services.audio import format_hhmmss

logger = logging.getLogger(__name__)

_whisper_model = None
_whisper_lock = threading.Lock()
_loaded_whisper_model_name = None

def get_whisper_model():
    global _whisper_model, _loaded_whisper_model_name
    name = os.getenv("WHISPER_MODEL", "small").strip()
    with _whisper_lock:
        if _whisper_model is not None and _loaded_whisper_model_name == name:
            return _whisper_model
        import whisper
        logger.info("Loading local Whisper model %r", name)
        _whisper_model = whisper.load_model(name)
        _loaded_whisper_model_name = name
    return _whisper_model

def get_openai_client_for_whisper() -> OpenAI:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise ValueError("Для транскрипции через OpenAI нужен OPENAI_API_KEY.")
    return OpenAI(api_key=key)

def _get_attr_or_key(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

def transcribe_chunk(path: Path, language: str = "ru"):
    backend = (os.getenv("WHISPER_BACKEND") or "local").strip().lower()
    if backend in ("api", "openai", "cloud"):
        wclient = get_openai_client_for_whisper()
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                with open(path, "rb") as f:
                    return wclient.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="verbose_json",
                        language=language,
                        timestamp_granularities=["segment"],
                    )
            except APIError as e:
                code = getattr(e, "status_code", None)
                if code in (500, 502, 503, 429) and attempt < max_attempts:
                    wait = min(2.0**attempt, 45.0)
                    time.sleep(wait)
                    continue
                raise

    model = get_whisper_model()
    result = model.transcribe(str(path), language=language, fp16=False, verbose=False)

    class Seg:
        __slots__ = ("start", "end", "text")
        def __init__(self, start: float, end: float, text: str):
            self.start = start; self.end = end; self.text = text
    class Tr:
        __slots__ = ("text", "segments")

    tr = Tr()
    tr.text = (result.get("text") or "").strip()
    segs = []
    for s in result.get("segments") or []:
        t = (_get_attr_or_key(s, "text", "") or "").strip()
        st = _get_attr_or_key(s, "start", None)
        en = _get_attr_or_key(s, "end", None)
        if st is None or en is None:
            continue
        segs.append(Seg(float(st), float(en), t))
    tr.segments = segs
    return tr

def transcribe_full_audio(chunks: list[Path]) -> tuple[str, list[dict]]:
    all_plain_parts = []
    all_segments = []

    for idx, chunk in enumerate(chunks, start=1):
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

def drop_whisper_model_cache() -> None:
    global _whisper_model, _loaded_whisper_model_name
    with _whisper_lock:
        _whisper_model = None
        _loaded_whisper_model_name = None

def _whisper_cache_dir() -> Path:
    default = Path.home() / ".cache"
    base = Path(os.getenv("XDG_CACHE_HOME", str(default)))
    return base / "whisper"

def _local_whisper_models_snapshot() -> dict:
    try:
        import whisper as whisper_pkg
    except ImportError as e:
        return {"cache_dir": None, "models": [], "error": "import_failed", "hint": str(e)}

    models_meta: list[dict] = []
    cache_dir = _whisper_cache_dir()
    reg = getattr(whisper_pkg, "_MODELS", {})
    for name in whisper_pkg.available_models():
        url = reg.get(name)
        if not url: continue
        fn = os.path.basename(url)
        p = cache_dir / fn
        downloaded = p.is_file()
        size_bytes = None
        if downloaded:
            try: size_bytes = p.stat().st_size
            except OSError: pass
        models_meta.append({"id": name, "file": fn, "downloaded": downloaded, "size_bytes": size_bytes})

    all_files = {m["file"] for m in models_meta}
    files_present = {m["file"] for m in models_meta if m.get("downloaded")}
    return {
        "cache_dir": str(cache_dir.resolve()),
        "models": models_meta,
        "downloaded_count": sum(1 for m in models_meta if m.get("downloaded")),
        "total_count": len(models_meta),
        "unique_pt_total": len(all_files),
        "unique_pt_downloaded": len(files_present),
        "error": None,
    }
