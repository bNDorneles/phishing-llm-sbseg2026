from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path

import pandas as pd

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    def tqdm(iterable, total=None, desc=None):
        return iterable

from src.config import ExperimentConfig, ModelConfig
from src.providers import LLMClient, LLMProviderError, LLMRequestFailed
from src.utils import content_hash, extract_json, failure_response, log_event, normalize_response

LOGGER = logging.getLogger(__name__)


def run_model_on_dataset(
    dataset: pd.DataFrame,
    model_config: ModelConfig,
    experiment: ExperimentConfig,
    run_dir: Path,
    limit: int | None = None,
) -> pd.DataFrame:
    rows = []
    raw_dir = run_dir / "raw_responses" / model_config.name
    raw_dir.mkdir(parents=True, exist_ok=True)
    eval_df = dataset.head(limit).copy() if limit else dataset.copy()
    expected_total = len(eval_df)

    try:
        client = LLMClient(
            model_config,
            retry_attempts=experiment.retry_attempts,
            retry_sleep_seconds=experiment.retry_sleep_seconds,
            request_timeout_seconds=experiment.request_timeout_seconds,
            backoff_base_seconds=experiment.backoff_base_seconds,
            backoff_max_seconds=experiment.backoff_max_seconds,
            groq_rate_limit_safety_factor=experiment.groq_rate_limit_safety_factor,
            groq_min_remaining_tokens=experiment.groq_min_remaining_tokens,
        )
    except Exception as exc:
        log_event(
            LOGGER,
            logging.ERROR,
            "model_initialization_failed",
            model=model_config.name,
            model_id=model_config.model_id,
            provider=model_config.provider,
            error_type=_error_type(exc),
            error_message=str(exc),
            expected_total=expected_total,
        )
        for _, row in eval_df.iterrows():
            rows.append(
                _build_failure_row(
                    row=row,
                    model_config=model_config,
                    request_id=_new_request_id(model_config.name, row["sample_id"]),
                    email_text=str(row["email_text"])[: experiment.max_email_chars],
                    raw_text="",
                    error_type=_error_type(exc),
                    error_message=str(exc),
                    attempts=0,
                    latency_seconds=0.0,
                    api_status_code=None,
                    provider_request_id="",
                )
            )
        results = pd.DataFrame(rows)
        _write_batch_summary(results, run_dir, model_config, expected_total)
        return results

    for _, row in tqdm(eval_df.iterrows(), total=expected_total, desc=model_config.name):
        sample_id = row["sample_id"]
        request_id = _new_request_id(model_config.name, sample_id)
        email_text = str(row["email_text"])[: experiment.max_email_chars]
        email_hash = content_hash(email_text)
        started = time.monotonic()
        raw_text = ""
        provider_request_id = ""
        attempts = 0
        latency_seconds = 0.0
        api_status_code = None

        log_event(
            LOGGER,
            logging.INFO,
            "email_processing_started",
            email_id=sample_id,
            email_hash=email_hash,
            request_id=request_id,
            model=model_config.name,
            model_id=model_config.model_id,
            provider=model_config.provider,
        )

        try:
            provider_result = client.analyze_with_metadata(
                email_text,
                sample_id=sample_id,
                correlation_id=request_id,
            )
            raw_text = provider_result.text
            attempts = provider_result.attempts
            latency_seconds = provider_result.latency_seconds
            api_status_code = provider_result.status_code
            provider_request_id = provider_result.provider_request_id
            payload = extract_json(raw_text)
            normalized = normalize_response(payload)
            row_result = _build_success_row(
                row=row,
                model_config=model_config,
                request_id=request_id,
                email_text=email_text,
                normalized=normalized,
                attempts=attempts,
                latency_seconds=latency_seconds,
                api_status_code=api_status_code,
                provider_request_id=provider_request_id,
            )
            log_event(
                LOGGER,
                logging.INFO,
                "email_processing_finished",
                email_id=sample_id,
                email_hash=email_hash,
                request_id=request_id,
                provider_request_id=provider_request_id,
                model=model_config.name,
                model_id=model_config.model_id,
                attempts=attempts,
                latency_seconds=round(time.monotonic() - started, 4),
                status_final="success",
                error_type="",
            )
        except Exception as exc:
            if isinstance(exc, LLMRequestFailed):
                attempts = exc.attempts
                latency_seconds = exc.latency_seconds
                api_status_code = exc.status_code
                provider_request_id = exc.provider_request_id
            else:
                latency_seconds = time.monotonic() - started
            error_type = _error_type(exc)
            row_result = _build_failure_row(
                row=row,
                model_config=model_config,
                request_id=request_id,
                email_text=email_text,
                raw_text=raw_text,
                error_type=error_type,
                error_message=str(exc),
                attempts=attempts,
                latency_seconds=latency_seconds,
                api_status_code=api_status_code,
                provider_request_id=provider_request_id,
            )
            log_event(
                LOGGER,
                logging.ERROR,
                "email_processing_finished",
                email_id=sample_id,
                email_hash=email_hash,
                request_id=request_id,
                provider_request_id=provider_request_id,
                model=model_config.name,
                model_id=model_config.model_id,
                attempts=attempts,
                latency_seconds=round(time.monotonic() - started, 4),
                status_final="failed",
                error_type=error_type,
                error_message=str(exc),
                api_status_code=api_status_code,
            )

        _write_raw_response(raw_dir, row_result, raw_text)
        rows.append(row_result)
        if model_config.provider != "mock" and experiment.sleep_between_requests_seconds > 0:
            time.sleep(experiment.sleep_between_requests_seconds)

    results = pd.DataFrame(rows)
    _write_batch_summary(results, run_dir, model_config, expected_total)
    return results


def _new_request_id(model: str, sample_id: str) -> str:
    return f"{model}:{sample_id}:{uuid.uuid4().hex[:12]}"


def _build_success_row(
    *,
    row: pd.Series,
    model_config: ModelConfig,
    request_id: str,
    email_text: str,
    normalized: dict,
    attempts: int,
    latency_seconds: float,
    api_status_code: int | None,
    provider_request_id: str,
) -> dict:
    return {
        "sample_id": row["sample_id"],
        "email_hash": content_hash(email_text),
        "request_id": request_id,
        "provider_request_id": provider_request_id,
        "true_label": row["true_label"],
        "model": model_config.name,
        "provider": model_config.provider,
        "model_id": model_config.model_id,
        "temperature": model_config.temperature,
        "status": "success",
        "error_type": "",
        "error_message": "",
        "parse_error": "",
        "attempts": attempts,
        "latency_seconds": round(latency_seconds, 4),
        "api_status_code": api_status_code,
        **normalized,
    }


def _build_failure_row(
    *,
    row: pd.Series,
    model_config: ModelConfig,
    request_id: str,
    email_text: str,
    raw_text: str,
    error_type: str,
    error_message: str,
    attempts: int,
    latency_seconds: float,
    api_status_code: int | None,
    provider_request_id: str,
) -> dict:
    return {
        "sample_id": row["sample_id"],
        "email_hash": content_hash(email_text),
        "request_id": request_id,
        "provider_request_id": provider_request_id,
        "true_label": row["true_label"],
        "model": model_config.name,
        "provider": model_config.provider,
        "model_id": model_config.model_id,
        "temperature": model_config.temperature,
        "status": "failed",
        "error_type": error_type,
        "error_message": error_message[:500],
        "parse_error": error_message[:500],
        "attempts": attempts,
        "latency_seconds": round(latency_seconds, 4),
        "api_status_code": api_status_code,
        **failure_response(),
    }


def _write_raw_response(raw_dir: Path, row_result: dict, raw_text: str) -> None:
    raw_payload = {
        "sample_id": row_result["sample_id"],
        "email_hash": row_result["email_hash"],
        "request_id": row_result["request_id"],
        "provider_request_id": row_result["provider_request_id"],
        "model": row_result["model"],
        "model_id": row_result["model_id"],
        "status": row_result["status"],
        "error_type": row_result["error_type"],
        "error_message": row_result["error_message"],
        "attempts": row_result["attempts"],
        "latency_seconds": row_result["latency_seconds"],
        "api_status_code": row_result["api_status_code"],
        "raw_response": raw_text,
    }
    (raw_dir / f"{row_result['sample_id']}.json").write_text(
        json.dumps(raw_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_batch_summary(results: pd.DataFrame, run_dir: Path, model_config: ModelConfig, expected_total: int) -> None:
    success_count = int((results["status"] == "success").sum()) if "status" in results.columns else 0
    failed_count = int((results["status"] == "failed").sum()) if "status" in results.columns else 0
    processed_total = success_count + failed_count
    summary = {
        "model": model_config.name,
        "model_id": model_config.model_id,
        "provider": model_config.provider,
        "total_entrada": expected_total,
        "total_processado_sucesso": success_count,
        "total_processado_falha": failed_count,
        "total_contabilizado": processed_total,
        "coverage_ok": expected_total == processed_total,
    }
    (run_dir / f"batch_summary_{model_config.name}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_event(LOGGER, logging.INFO, "batch_finished", **summary)
    if expected_total != processed_total:
        log_event(LOGGER, logging.ERROR, "batch_coverage_failed", **summary)
        raise RuntimeError(
            f"Cobertura invalida para {model_config.name}: entrada={expected_total}, contabilizado={processed_total}"
        )
    log_event(LOGGER, logging.INFO, "batch_coverage_validated", **summary)


def _error_type(exc: Exception) -> str:
    if isinstance(exc, (LLMProviderError, LLMRequestFailed)):
        return exc.error_type
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, (json.JSONDecodeError, ValueError, KeyError, TypeError)):
        return "validation"
    return exc.__class__.__name__
