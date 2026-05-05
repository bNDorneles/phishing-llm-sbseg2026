from __future__ import annotations

import json
import logging
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from src.red_flags import RED_FLAGS


def setup_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True))


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    label = str(payload.get("classification", "")).strip().lower()
    if label not in {"phishing", "safe"}:
        label = "phishing" if "phish" in label else "safe"

    red_flags = payload.get("red_flags", {}) or {}
    normalized_flags = {flag: int(bool(red_flags.get(flag, 0))) for flag in RED_FLAGS}

    scores = payload.get("scores", {}) or {}
    normalized_scores = {
        "score_risco_geral": _bounded_int(scores.get("risco_geral", 0)),
        "score_confianca": _bounded_int(scores.get("confianca", 0)),
        "score_urgencia": _bounded_int(scores.get("urgencia", 0)),
        "score_solicitacao_sensivel": _bounded_int(scores.get("solicitacao_sensivel", 0)),
        "score_suspeita_links": _bounded_int(scores.get("suspeita_links", 0)),
    }
    return {
        "predicted_label": label,
        "probability": _bounded_float(payload.get("probability", 0.0)),
        **normalized_flags,
        **normalized_scores,
        "explanation": str(payload.get("explanation", ""))[:500],
    }


def failure_response() -> dict[str, Any]:
    return {
        "predicted_label": "",
        "probability": 0.0,
        **{flag: 0 for flag in RED_FLAGS},
        "score_risco_geral": 0,
        "score_confianca": 0,
        "score_urgencia": 0,
        "score_solicitacao_sensivel": 0,
        "score_suspeita_links": 0,
        "explanation": "",
    }


def _bounded_int(value: Any) -> int:
    try:
        return max(0, min(10, int(float(value))))
    except (TypeError, ValueError):
        return 0


def _bounded_float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
