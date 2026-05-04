from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pandas as pd

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    def tqdm(iterable, total=None, desc=None):
        return iterable

from src.config import ExperimentConfig, ModelConfig
from src.providers import LLMClient
from src.utils import extract_json, normalize_response

LOGGER = logging.getLogger(__name__)


def run_model_on_dataset(
    dataset: pd.DataFrame,
    model_config: ModelConfig,
    experiment: ExperimentConfig,
    run_dir: Path,
    limit: int | None = None,
) -> pd.DataFrame:
    client = LLMClient(
        model_config,
        retry_attempts=experiment.retry_attempts,
        retry_sleep_seconds=experiment.retry_sleep_seconds,
    )
    rows = []
    raw_dir = run_dir / "raw_responses" / model_config.name
    raw_dir.mkdir(parents=True, exist_ok=True)
    eval_df = dataset.head(limit).copy() if limit else dataset.copy()

    for _, row in tqdm(eval_df.iterrows(), total=len(eval_df), desc=model_config.name):
        sample_id = row["sample_id"]
        email_text = str(row["email_text"])[: experiment.max_email_chars]
        raw_text = ""
        parse_error = ""
        try:
            raw_text = client.analyze(email_text)
            payload = extract_json(raw_text)
            normalized = normalize_response(payload)
        except Exception as exc:
            LOGGER.exception("Falha ao processar %s com %s", sample_id, model_config.name)
            parse_error = str(exc)
            normalized = {
                "predicted_label": "safe",
                "probability": 0.0,
                "explanation": "",
            }
        raw_payload = {
            "sample_id": sample_id,
            "model": model_config.name,
            "raw_response": raw_text,
            "parse_error": parse_error,
        }
        (raw_dir / f"{sample_id}.json").write_text(
            json.dumps(raw_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rows.append(
            {
                "sample_id": sample_id,
                "true_label": row["true_label"],
                "model": model_config.name,
                "provider": model_config.provider,
                "model_id": model_config.model_id,
                "temperature": model_config.temperature,
                **normalized,
                "parse_error": parse_error,
            }
        )
        if model_config.provider != "mock" and experiment.sleep_between_requests_seconds > 0:
            time.sleep(experiment.sleep_between_requests_seconds)
    return pd.DataFrame(rows)
