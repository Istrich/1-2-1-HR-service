import os
import re
import logging
from typing import Any
from openai import OpenAI, APIError

logger = logging.getLogger(__name__)

DEEPSEEK_API_BASE = "https://api.deepseek.com"

SYSTEM_REPORT_PROMPT = """
Ты — профессиональный HR-аналитик, специализирующийся на оценке настроений, вовлечённости и рисков сотрудников.
Твоя задача — сформировать аналитический отчёт по транскрипции 1–2–1 интервью.
Работай как эксперт-разработчик HR-аналитических заключений...
"""

DEFAULT_REPORT_PROMPT = """
Проанализируй транскрипцию 1–2–1 интервью ниже и сформируй структурированный аналитический отчёт.
"""

DEFAULT_EMAIL_PROMPT = """
Ты опытный HR-бизнес-партнёр.
На основе транскрипции 1-2-1 встречи с сотрудником сформируй черновик делового письма.
"""

REFINE_SYSTEM_PROMPT = """
Ты — профессиональный HR-аналитик. Тебе дан аналитический отчёт по 1-2-1 интервью и комментарий с просьбой доработать отчёт.
Верни полный текст обновлённого отчёта, не только изменённые части.
"""

def get_report_llm() -> tuple[OpenAI, str]:
    provider = (os.getenv("REPORT_AI_PROVIDER") or "openai").strip().lower()
    if provider == "deepseek":
        key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
        if not key:
            raise ValueError("Не задан ключ DeepSeek.")
        model = (os.getenv("DEEPSEEK_MODEL") or "deepseek-chat").strip()
        return OpenAI(api_key=key, base_url=DEEPSEEK_API_BASE), model

    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise ValueError("Не задан ключ OpenAI.")
    model = (os.getenv("OPENAI_REPORT_MODEL") or "gpt-4o").strip()
    return OpenAI(api_key=key), model

def chat_completion(
    client: OpenAI,
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 16000,
) -> str:
    provider = (os.getenv("REPORT_AI_PROVIDER") or "openai").strip().lower()
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    if provider == "deepseek":
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = temperature
    else:
        kwargs["max_completion_tokens"] = max_tokens
        if not _openai_model_fixed_temperature_only(model):
            kwargs["temperature"] = temperature

    last_err: APIError | None = None
    for _ in range(8):
        try:
            r = client.chat.completions.create(**kwargs)
            if not r.choices:
                raise ValueError("Модель вернула пустой ответ")
            return (r.choices[0].message.content or "").strip()
        except APIError as e:
            last_err = e
            if getattr(e, "status_code", None) != 400:
                raise
            msg = (str(e) or "").lower()
            changed = False
            if "temperature" in kwargs and ("temperature" in msg or "unsupported_value" in msg):
                kwargs.pop("temperature", None)
                changed = True
                logger.info("chat.completions: повтор без temperature")
            elif provider != "deepseek":
                if "max_completion_tokens" in kwargs and ("use 'max_tokens'" in msg or "unsupported" in msg or "invalid" in msg):
                    kwargs.pop("max_completion_tokens", None)
                    kwargs["max_tokens"] = max_tokens
                    changed = True
                    logger.info("chat.completions: повтор с max_tokens")
                elif "max_tokens" in kwargs and ("max_completion_tokens" in msg and ("instead" in msg or "unsupported" in msg or "invalid" in msg)):
                    kwargs.pop("max_tokens", None)
                    kwargs["max_completion_tokens"] = max_tokens
                    changed = True
                    logger.info("chat.completions: повтор с max_completion_tokens")
            if not changed:
                raise
    if last_err:
        raise last_err
    raise RuntimeError("chat.completions: исчерпаны повторы")

def _openai_model_fixed_temperature_only(model: str) -> bool:
    m = (model or "").strip().lower()
    return re.match(r"^o\d", m) or m.startswith("gpt-5")

def build_report(transcript: str, report_prompt: str) -> str:
    llm, model = get_report_llm()
    messages = [
        {"role": "system", "content": SYSTEM_REPORT_PROMPT.strip()},
        {"role": "user", "content": f"{report_prompt.strip()}\n\n---\n\nТранскрипция:\n\n{transcript}"},
    ]
    return chat_completion(llm, model, messages, temperature=0.2)

def refine_report(current_report: str, transcript: str, comment: str) -> str:
    llm, model = get_report_llm()
    messages = [
        {"role": "system", "content": REFINE_SYSTEM_PROMPT.strip()},
        {"role": "user", "content": f"Транскрипция интервью:\n\n{transcript}\n\n---\n\nТекущий отчёт:\n\n{current_report}\n\n---\n\nКомментарий:\n\n{comment}"},
    ]
    return chat_completion(llm, model, messages, temperature=0.25)

def build_email(transcript: str, email_prompt: str) -> str:
    llm, model = get_report_llm()
    messages = [
        {"role": "system", "content": email_prompt.strip()},
        {"role": "user", "content": f"Транскрипция встречи:\n\n{transcript}"},
    ]
    return chat_completion(llm, model, messages, temperature=0.3)

OPENAI_REPORT_MODEL_PRESETS: list[tuple[str, str]] = [
    ("gpt-4o", "GPT-4o"),
    ("gpt-4o-mini", "GPT-4o mini"),
    ("o1", "o1"),
    ("o1-mini", "o1-mini"),
    ("o3-mini", "o3-mini"),
]

def _openai_report_model_presets_payload() -> list[dict[str, str]]:
    return [{"id": mid, "label": lab} for mid, lab in OPENAI_REPORT_MODEL_PRESETS]

def _is_likely_chat_completion_model(model_id: str) -> bool:
    mid = (model_id or "").strip().lower()
    if not mid: return False
    block_any = ("embedding", "embed", "whisper", "dall-e", "tts", "moderation", "realtime", "transcribe")
    if any(x in mid for x in block_any): return False
    if mid.startswith("gpt-") or mid.startswith("chatgpt-") or re.match(r"^o[0-9]", mid): return True
    return False

import asyncio
def _fetch_openai_models_sync() -> list[dict[str, str]]:
    from app.services.llm import get_report_llm
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key: raise ValueError("no_openai_key")
    client = OpenAI(api_key=key)
    resp = client.models.list()
    raw = [getattr(m, "id", "").strip() for m in resp.data if getattr(m, "id", "").strip()]
    out = [{"id": mid, "label": mid} for mid in raw if _is_likely_chat_completion_model(mid)]
    out.sort(key=lambda x: x["id"].lower())
    return out

async def _fetch_openai_models_live() -> list[dict[str, str]]:
    return await asyncio.to_thread(_fetch_openai_models_sync)

def _valid_openai_report_model_id(m: str) -> bool:
    s = (m or "").strip()
    if not s or len(s) > 128: return False
    ids = {x[0] for x in OPENAI_REPORT_MODEL_PRESETS}
    if s in ids: return True
    return bool(re.fullmatch(r"[a-zA-Z0-9._-]+", s))
