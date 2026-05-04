from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict
from typing import Any

try:
    import requests
except ModuleNotFoundError:
    requests = None

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        return None

from src.config import ModelConfig
from src.prompts import SYSTEM_PROMPT, build_user_prompt
from src.red_flags import RED_FLAGS

load_dotenv()


class LLMClient:
    def __init__(self, config: ModelConfig, retry_attempts: int = 3, retry_sleep_seconds: int = 2):
        self.config = config
        self.retry_attempts = retry_attempts
        self.retry_sleep_seconds = retry_sleep_seconds

    def analyze(self, email_text: str) -> str:
        if self.config.provider == "mock":
            return json.dumps(mock_analysis(email_text), ensure_ascii=False)
        for attempt in range(1, self.retry_attempts + 1):
            try:
                return self._call_provider(email_text)
            except Exception:
                if attempt == self.retry_attempts:
                    raise
                time.sleep(self.retry_sleep_seconds * attempt)
        raise RuntimeError("Falha inesperada de retry")

    def _call_provider(self, email_text: str) -> str:
        provider = self.config.provider
        if provider == "groq":
            return _chat_completion(
                base_url="https://api.groq.com/openai/v1/chat/completions",
                api_key=os.environ["GROQ_API_KEY"],
                config=self.config,
                email_text=email_text,
            )
        raise ValueError(f"Provider nao suportado: {provider}")


def _chat_completion(base_url: str, api_key: str, config: ModelConfig, email_text: str) -> str:
    if requests is None:
        raise RuntimeError("Instale requests para usar a API Groq.")
    payload = {
        "model": config.model_id,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(email_text)},
        ],
    }
    response = requests.post(
        base_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


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
        "remetente_falsificado": r"on behalf of|reply-to|spoof|do-not-reply",
        "historias_elaboradas": r"widow|inheritance|prince|foreign account|fund transfer",
        "personalizacao_excessiva": r"we know|your recent|personal record|case number",
        "falta_contato": r"do not call|no phone|only reply",
        "conteudo_emocional": r"fear|help me|threat|legal action|final warning",
        "inconsistencias_contato": r"reply to.*@gmail|contact.*@yahoo|different email",
        "anexos_estranhos": r"\.zip|\.rar|\.7z|macro|enable content",
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
