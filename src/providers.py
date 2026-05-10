from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from dataclasses import asdict, dataclass
from typing import Any

try:
    import requests
except ModuleNotFoundError:
    requests = None

try:
    from dotenv import load_dotenv as _load_dotenv
except ModuleNotFoundError:
    _load_dotenv = None

from src.config import ModelConfig, ROOT
from src.prompts import SYSTEM_PROMPT, build_compact_user_prompt, build_user_prompt
from src.red_flags import RED_FLAGS
from src.utils import log_event

LOGGER = logging.getLogger(__name__)

RETRIABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
NON_RETRIABLE_STATUS_CODES = {400, 401, 403, 404, 422}
GROQ_DOCUMENTED_LIMITS = {
    # Values from https://console.groq.com/docs/rate-limits.
    "openai/gpt-oss-120b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200000},
    "llama-3.3-70b-versatile": {"rpm": 30, "rpd": 1000, "tpm": 12000, "tpd": 100000},
    "groq/compound": {"rpm": 30, "rpd": 250, "tpm": 70000, "tpd": None},
    "qwen/qwen3-32b": {"rpm": 60, "rpd": 1000, "tpm": 6000, "tpd": 500000},
}


@dataclass(frozen=True)
class ProviderResult:
    text: str
    attempts: int
    latency_seconds: float
    status_code: int | None = None
    provider_request_id: str = ""
    rate_limit: dict[str, Any] | None = None
    json_mode_fallback_used: bool = False


class LLMProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        retriable: bool,
        status_code: int | None = None,
        provider_request_id: str = "",
        retry_after_seconds: float | None = None,
        rate_limit: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.retriable = retriable
        self.status_code = status_code
        self.provider_request_id = provider_request_id
        self.retry_after_seconds = retry_after_seconds
        self.rate_limit = rate_limit or {}


class LLMRequestFailed(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        attempts: int,
        latency_seconds: float,
        retriable: bool,
        status_code: int | None = None,
        provider_request_id: str = "",
        rate_limit: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.attempts = attempts
        self.latency_seconds = latency_seconds
        self.retriable = retriable
        self.status_code = status_code
        self.provider_request_id = provider_request_id
        self.rate_limit = rate_limit or {}


class LLMClient:
    def __init__(
        self,
        config: ModelConfig,
        retry_attempts: int = 3,
        retry_sleep_seconds: float = 2,
        request_timeout_seconds: float = 90,
        backoff_base_seconds: float = 1,
        backoff_max_seconds: float = 30,
        groq_rate_limit_safety_factor: float = 1.2,
        groq_min_remaining_tokens: int = 0,
    ):
        self.config = config
        self.retry_attempts = max(1, int(_env_number("LLM_MAX_ATTEMPTS", retry_attempts)))
        self.retry_sleep_seconds = float(retry_sleep_seconds)
        self.request_timeout_seconds = float(_env_number("LLM_REQUEST_TIMEOUT_SECONDS", request_timeout_seconds))
        self.backoff_base_seconds = float(_env_number("LLM_BACKOFF_BASE_SECONDS", backoff_base_seconds))
        self.backoff_max_seconds = float(_env_number("LLM_BACKOFF_MAX_SECONDS", backoff_max_seconds))
        self.groq_rate_limit_safety_factor = float(
            _env_number("GROQ_RATE_LIMIT_SAFETY_FACTOR", groq_rate_limit_safety_factor)
        )
        self.groq_min_remaining_tokens = int(_env_number("GROQ_MIN_REMAINING_TOKENS", groq_min_remaining_tokens))
        self.next_allowed_at = 0.0
        self.api_key = _required_api_key("GROQ_API_KEY") if config.provider == "groq" else None

    def analyze(self, email_text: str) -> str:
        return self.analyze_with_metadata(email_text).text

    def analyze_with_metadata(
        self,
        email_text: str,
        *,
        sample_id: str = "",
        correlation_id: str = "",
    ) -> ProviderResult:
        if self.config.provider == "mock":
            started = time.monotonic()
            return ProviderResult(
                text=json.dumps(mock_analysis(email_text), ensure_ascii=False),
                attempts=1,
                latency_seconds=time.monotonic() - started,
            )

        total_started = time.monotonic()
        last_error: LLMProviderError | None = None
        use_json_mode = True
        json_mode_fallback_used = False
        for attempt in range(1, self.retry_attempts + 1):
            self._wait_for_groq_rate_limit(email_text, sample_id=sample_id, correlation_id=correlation_id)
            attempt_started = time.monotonic()
            log_event(
                LOGGER,
                logging.DEBUG,
                "api_attempt_started",
                email_id=sample_id,
                request_id=correlation_id,
                model=self.config.name,
                model_id=self.config.model_id,
                attempt=attempt,
                max_attempts=self.retry_attempts,
                timeout_seconds=self.request_timeout_seconds,
                json_mode=use_json_mode,
            )
            try:
                text, status_code, provider_request_id, rate_limit = self._call_provider(email_text, json_mode=use_json_mode)
                self._schedule_next_groq_request(email_text, rate_limit)
                attempt_latency = time.monotonic() - attempt_started
                total_latency = time.monotonic() - total_started
                log_event(
                    LOGGER,
                    logging.INFO,
                    "api_attempt_finished",
                    email_id=sample_id,
                    request_id=correlation_id,
                    provider_request_id=provider_request_id,
                    model=self.config.name,
                    model_id=self.config.model_id,
                    attempt=attempt,
                    latency_seconds=round(attempt_latency, 4),
                    status_final="success",
                    status_code=status_code,
                    rate_limit=rate_limit,
                    json_mode=use_json_mode,
                    json_mode_fallback_used=json_mode_fallback_used,
                )
                return ProviderResult(
                    text=text,
                    attempts=attempt,
                    latency_seconds=total_latency,
                    status_code=status_code,
                    provider_request_id=provider_request_id,
                    rate_limit=rate_limit,
                    json_mode_fallback_used=json_mode_fallback_used,
                )
            except LLMProviderError as exc:
                last_error = exc
                self._schedule_next_groq_request(email_text, exc.rate_limit)
                attempt_latency = time.monotonic() - attempt_started
                json_mode_can_fallback = (
                    exc.error_type == "json_mode_validation"
                    and use_json_mode
                    and self.config.provider == "groq"
                    and attempt < self.retry_attempts
                )
                log_level = logging.WARNING if (exc.retriable or json_mode_can_fallback) and attempt < self.retry_attempts else logging.ERROR
                log_event(
                    LOGGER,
                    log_level,
                    "api_attempt_finished",
                    email_id=sample_id,
                    request_id=correlation_id,
                    provider_request_id=exc.provider_request_id,
                    model=self.config.name,
                    model_id=self.config.model_id,
                    attempt=attempt,
                    latency_seconds=round(attempt_latency, 4),
                    status_final="failed",
                    error_type=exc.error_type,
                    error_message=str(exc),
                    retriable=exc.retriable,
                    status_code=exc.status_code,
                    retry_after_seconds=exc.retry_after_seconds,
                    rate_limit=exc.rate_limit,
                    json_mode=use_json_mode,
                )
                if json_mode_can_fallback:
                    use_json_mode = False
                    json_mode_fallback_used = True
                    sleep_seconds = self._retry_delay_seconds(exc, attempt)
                    log_event(
                        LOGGER,
                        logging.WARNING,
                        "api_json_mode_fallback_scheduled",
                        email_id=sample_id,
                        request_id=correlation_id,
                        provider_request_id=exc.provider_request_id,
                        model=self.config.name,
                        model_id=self.config.model_id,
                        attempt=attempt,
                        next_attempt=attempt + 1,
                        error_type=exc.error_type,
                        sleep_seconds=round(sleep_seconds, 4),
                    )
                    time.sleep(sleep_seconds)
                    continue
                if not exc.retriable or attempt >= self.retry_attempts:
                    break
                sleep_seconds = self._retry_delay_seconds(exc, attempt)
                log_event(
                    LOGGER,
                    logging.WARNING,
                    "api_retry_scheduled",
                    email_id=sample_id,
                    request_id=correlation_id,
                    provider_request_id=exc.provider_request_id,
                    model=self.config.name,
                    model_id=self.config.model_id,
                    attempt=attempt,
                    next_attempt=attempt + 1,
                    error_type=exc.error_type,
                    sleep_seconds=round(sleep_seconds, 4),
                    retry_after_seconds=exc.retry_after_seconds,
                )
                time.sleep(sleep_seconds)

        total_latency = time.monotonic() - total_started
        if last_error is None:
            last_error = LLMProviderError(
                "Falha desconhecida sem excecao capturada.",
                error_type="unknown",
                retriable=False,
            )
        raise LLMRequestFailed(
            str(last_error),
            error_type=last_error.error_type,
            attempts=min(self.retry_attempts, max(1, attempt if "attempt" in locals() else 1)),
            latency_seconds=total_latency,
            retriable=last_error.retriable,
            status_code=last_error.status_code,
            provider_request_id=last_error.provider_request_id,
            rate_limit=last_error.rate_limit,
        )

    def _call_provider(self, email_text: str, *, json_mode: bool = True) -> tuple[str, int | None, str, dict[str, Any]]:
        provider = self.config.provider
        if provider == "groq":
            return _chat_completion(
                base_url="https://api.groq.com/openai/v1/chat/completions",
                api_key=self.api_key or "",
                config=self.config,
                email_text=email_text,
                timeout_seconds=self.request_timeout_seconds,
                json_mode=json_mode,
            )
        raise LLMProviderError(
            f"Provider nao suportado: {provider}",
            error_type="configuration",
            retriable=False,
        )

    def _wait_for_groq_rate_limit(self, email_text: str, *, sample_id: str, correlation_id: str) -> None:
        if self.config.provider != "groq":
            return
        sleep_seconds = max(0.0, self.next_allowed_at - time.monotonic())
        if sleep_seconds <= 0:
            return
        log_event(
            LOGGER,
            logging.INFO,
            "groq_rate_limit_wait",
            email_id=sample_id,
            request_id=correlation_id,
            model=self.config.name,
            model_id=self.config.model_id,
            sleep_seconds=round(sleep_seconds, 4),
            estimated_tokens=_estimate_request_tokens(email_text, self.config.max_tokens),
        )
        time.sleep(sleep_seconds)

    def _schedule_next_groq_request(self, email_text: str, rate_limit: dict[str, Any] | None) -> None:
        if self.config.provider != "groq":
            return
        wait_seconds = self._documented_rate_limit_wait(email_text)
        header_wait = _header_based_wait_seconds(rate_limit or {}, self.groq_min_remaining_tokens)
        wait_seconds = max(wait_seconds, header_wait)
        self.next_allowed_at = max(self.next_allowed_at, time.monotonic() + wait_seconds)

    def _documented_rate_limit_wait(self, email_text: str) -> float:
        estimated_tokens = _estimate_request_tokens(email_text, self.config.max_tokens)
        return _documented_min_request_interval_seconds(
            model_id=self.config.model_id,
            estimated_tokens=estimated_tokens,
            safety_factor=self.groq_rate_limit_safety_factor,
        )

    def _retry_delay_seconds(self, exc: LLMProviderError, attempt: int) -> float:
        jitter_delay = _full_jitter_delay(
            attempt=attempt,
            base_seconds=self.backoff_base_seconds or self.retry_sleep_seconds,
            max_seconds=self.backoff_max_seconds,
        )
        if exc.retry_after_seconds is None:
            return jitter_delay
        # Groq sets retry-after on 429. Treat it as authoritative and add a tiny jitter
        # to avoid synchronized retries if multiple runs are started together.
        return max(float(exc.retry_after_seconds), jitter_delay) + random.uniform(0, 0.25)


def _chat_completion(
    base_url: str,
    api_key: str,
    config: ModelConfig,
    email_text: str,
    timeout_seconds: float,
    json_mode: bool = True,
) -> tuple[str, int | None, str, dict[str, Any]]:
    if requests is None:
        raise LLMProviderError(
            "Instale requests para usar a API Groq.",
            error_type="configuration",
            retriable=False,
        )
    messages = _build_messages(config, email_text)
    payload = {
        "model": config.model_id,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "messages": messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        response = requests.post(
            base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout_seconds,
        )
    except requests.exceptions.Timeout as exc:
        raise LLMProviderError(
            f"Timeout apos {timeout_seconds}s",
            error_type="timeout",
            retriable=True,
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise LLMProviderError(
            str(exc),
            error_type="network",
            retriable=True,
        ) from exc

    provider_request_id = response.headers.get("x-request-id") or response.headers.get("x-groq-request-id") or ""
    rate_limit = _parse_groq_rate_limit_headers(response.headers)
    if response.status_code in RETRIABLE_STATUS_CODES:
        retry_after_seconds = rate_limit.get("retry_after_seconds") or _parse_retry_after_from_body(response.text)
        raise LLMProviderError(
            _response_error_message(response),
            error_type="rate_limit" if response.status_code == 429 else "server_error",
            retriable=True,
            status_code=response.status_code,
            provider_request_id=provider_request_id,
            retry_after_seconds=retry_after_seconds,
            rate_limit=rate_limit,
        )
    if response.status_code in NON_RETRIABLE_STATUS_CODES or response.status_code >= 400:
        error_type = _non_retriable_error_type(response.status_code, response.text)
        raise LLMProviderError(
            _response_error_message(response),
            error_type=error_type,
            retriable=False,
            status_code=response.status_code,
            provider_request_id=provider_request_id,
            rate_limit=rate_limit,
        )

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError(
            f"Resposta da API sem JSON esperado: {exc}",
            error_type="validation",
            retriable=False,
            status_code=response.status_code,
            provider_request_id=provider_request_id,
            rate_limit=rate_limit,
        ) from exc
    return str(content), response.status_code, provider_request_id, rate_limit


def _build_messages(config: ModelConfig, email_text: str) -> list[dict[str, str]]:
    if config.model_id == "groq/compound":
        return [{"role": "user", "content": build_compact_user_prompt(email_text)}]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(email_text)},
    ]


def load_project_env() -> None:
    env_path = ROOT / ".env"
    if _load_dotenv is not None:
        _load_dotenv(dotenv_path=env_path, override=True)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and not os.environ.get(key):
            os.environ[key] = value


def _required_api_key(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise LLMProviderError(
            f"{name} nao encontrada. Crie um arquivo .env na raiz do projeto com {name}=sua_chave "
            f"ou defina a variavel no terminal antes de executar.",
            error_type="configuration",
            retriable=False,
        )
    return value


def _env_number(name: str, default: float | int) -> float:
    value = os.environ.get(name)
    if value is None or str(value).strip() == "":
        return float(default)
    try:
        return float(value)
    except ValueError:
        return float(default)


def _full_jitter_delay(attempt: int, base_seconds: float, max_seconds: float) -> float:
    cap = min(max_seconds, base_seconds * (2 ** max(0, attempt - 1)))
    return random.uniform(0, cap)


def _estimate_request_tokens(email_text: str, max_output_tokens: int) -> int:
    prompt = f"{SYSTEM_PROMPT}\n{build_user_prompt(email_text)}"
    prompt_tokens_estimate = max(1, len(prompt) // 4)
    return prompt_tokens_estimate + int(max_output_tokens)


def _documented_min_request_interval_seconds(model_id: str, estimated_tokens: int, safety_factor: float = 1.2) -> float:
    limits = GROQ_DOCUMENTED_LIMITS.get(model_id)
    if not limits:
        return 0.0
    waits = []
    rpm = limits.get("rpm")
    if rpm:
        waits.append(60.0 / float(rpm))
    tpm = limits.get("tpm")
    if tpm:
        waits.append(60.0 * max(1, estimated_tokens) / float(tpm))
    # Compound has its own documented TPM, but runtime 429s can come from
    # internal routed models. Use the smallest configured Groq TPM as a
    # conservative floor for long research runs.
    if model_id == "groq/compound":
        internal_tpms = [item["tpm"] for key, item in GROQ_DOCUMENTED_LIMITS.items() if key != model_id and item.get("tpm")]
        if internal_tpms:
            waits.append(60.0 * max(1, estimated_tokens) / float(min(internal_tpms)))
    if not waits:
        return 0.0
    return max(waits) * max(1.0, safety_factor)


def _parse_groq_rate_limit_headers(headers) -> dict[str, Any]:
    return {
        "retry_after_seconds": _parse_seconds_header(headers.get("retry-after")),
        "limit_requests": _parse_int_header(headers.get("x-ratelimit-limit-requests")),
        "limit_tokens": _parse_int_header(headers.get("x-ratelimit-limit-tokens")),
        "remaining_requests": _parse_int_header(headers.get("x-ratelimit-remaining-requests")),
        "remaining_tokens": _parse_int_header(headers.get("x-ratelimit-remaining-tokens")),
        "reset_requests_seconds": _parse_duration_header(headers.get("x-ratelimit-reset-requests")),
        "reset_tokens_seconds": _parse_duration_header(headers.get("x-ratelimit-reset-tokens")),
    }


def _header_based_wait_seconds(rate_limit: dict[str, Any], min_remaining_tokens: int) -> float:
    waits = []
    remaining_tokens = rate_limit.get("remaining_tokens")
    reset_tokens = rate_limit.get("reset_tokens_seconds")
    if remaining_tokens is not None and reset_tokens is not None and remaining_tokens <= min_remaining_tokens:
        waits.append(float(reset_tokens))

    remaining_requests = rate_limit.get("remaining_requests")
    reset_requests = rate_limit.get("reset_requests_seconds")
    if remaining_requests is not None and reset_requests is not None and remaining_requests <= 0:
        waits.append(float(reset_requests))

    retry_after = rate_limit.get("retry_after_seconds")
    if retry_after is not None:
        waits.append(float(retry_after))

    return max(waits) if waits else 0.0


def _parse_seconds_header(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return _parse_duration_header(value)


def _parse_retry_after_from_body(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"try again in\s+(\d+(?:\.\d+)?)\s*(ms|s|m)", text, flags=re.IGNORECASE)
    if not match:
        return None
    amount, unit = match.groups()
    number = float(amount)
    if unit.lower() == "ms":
        return number / 1000.0
    if unit.lower() == "m":
        return number * 60.0
    return number


def _parse_int_header(value: str | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def _parse_duration_header(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().lower()
    matches = re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h)", text)
    if not matches:
        try:
            return float(text)
        except ValueError:
            return None
    total = 0.0
    for amount, unit in matches:
        number = float(amount)
        if unit == "ms":
            total += number / 1000.0
        elif unit == "s":
            total += number
        elif unit == "m":
            total += number * 60.0
        elif unit == "h":
            total += number * 3600.0
    return total


def _response_error_message(response) -> str:
    text = response.text or ""
    if len(text) > 500:
        text = text[:500] + "...[truncated]"
    return f"HTTP {response.status_code}: {text}"


def _non_retriable_error_type(status_code: int, response_text: str = "") -> str:
    if status_code in {401, 403}:
        return "auth"
    if status_code == 404:
        return "model_not_found"
    if status_code in {400, 422}:
        if _is_json_mode_validation_error(response_text):
            return "json_mode_validation"
        return "validation"
    return "http_error"


def _is_json_mode_validation_error(response_text: str) -> bool:
    text = (response_text or "").lower()
    return "json_validate_failed" in text or "failed_generation" in text


load_project_env()


def mock_analysis(email_text: str) -> dict[str, Any]:
    text = email_text.lower()
    patterns = {
        "remetente_suspeito": r"from:.*(noreply|support|security|admin).*@.*\.(ru|cn|xyz|top)",
        "senso_urgencia_medo": r"urgent|immediately|suspended|verify now|act now|limited time|expire",
        "solicitacao_dados_sensiveis": r"password|ssn|credit card|bank account|login|credentials",
        "links_suspeitos": r"http[s]?://|click here|bit\.ly|tinyurl|login",
        "erros_gramaticais": r"dear customer|kindly|congratulation|you has|verify your account",
        "email_nao_solicitado": r"winner|selected|lottery|prize|unexpected",
        "saudacao_generica": r"dear customer|dear user|valued customer",
        "anexos_suspeitos": r"attachment|invoice\.zip|\.exe|\.scr|\.bat",
        "formatacao_estranha": r"!!!|\$\$\$|<html>|font-size|all caps",
        "oferta_boa_demais": r"free money|prize|lottery|million|gift card|reward",
        "dominio_suspeito": r"\.(ru|cn|xyz|top|tk)|paypal-|google-verify|bank-secure",
        "historias_elaboradas": r"widow|inheritance|prince|foreign account|fund transfer",
        "personalizacao_excessiva": r"we know|your recent|personal record|case number",
        "contato_ausente_ou_inconsistente": r"do not call|no phone|only reply|reply to.*@gmail|contact.*@yahoo|different email",
        "conteudo_emocional": r"fear|help me|threat|legal action|final warning",
        "endereco_resposta_diferente": r"reply-to|respond to this address",
        "botoes_enganosos": r"button|click the button|confirm button|secure button",
    }
    flags = {flag: int(bool(re.search(pattern, text, flags=re.DOTALL))) for flag, pattern in patterns.items()}
    risk = sum(flags.values())
    phishing = risk >= 3
    probability = min(0.98, max(0.02, risk / max(len(RED_FLAGS), 1) + (0.35 if phishing else 0.05)))
    return {
        "classification": "phishing" if phishing else "safe",
        "probability": round(probability, 3),
        "red_flags": flags,
        "scores": {
            "risco_geral": min(10, risk),
            "confianca": 7 if risk else 5,
            "urgencia": 10 if flags["senso_urgencia_medo"] else 0,
            "solicitacao_sensivel": 10 if flags["solicitacao_dados_sensiveis"] else 0,
            "suspeita_links": 10 if flags["links_suspeitos"] else 0,
        },
        "explanation": "Classificacao heuristica local usada apenas para validar o pipeline.",
        "model_config": asdict(ModelConfig("mock", "mock", True, "heuristic-mock", 0.0, 700)),
    }
