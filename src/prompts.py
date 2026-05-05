from __future__ import annotations

import json

from src.red_flags import RED_FLAGS


SYSTEM_PROMPT = """Voce e um avaliador academico de seguranca cibernetica especializado em phishing.
Analise o email com criterio consistente. Responda apenas JSON valido, sem markdown."""


def build_user_prompt(email_text: str) -> str:
    flags = json.dumps(RED_FLAGS, ensure_ascii=False)
    schema = {
        "classification": "phishing|safe",
        "probability": 0.0,
        "red_flags": {flag: 0 for flag in RED_FLAGS},
        "scores": {
            "risco_geral": 0,
            "confianca": 0,
            "urgencia": 0,
            "solicitacao_sensivel": 0,
            "suspeita_links": 0,
        },
        "explanation": "max 120 chars",
    }
    return f"""Tarefa: classificar o email como phishing ou safe e marcar red flags.
Responda somente um objeto JSON minificado, sem texto antes/depois.
Use exatamente estas chaves: classification, probability, red_flags, scores, explanation.
classification deve ser "phishing" ou "safe". probability deve ser numero entre 0 e 1.
Cada red flag deve ser 1 se presente ou 0 se ausente. Nao adicione campos.
Red flags: {flags}
Schema: {json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}
Email:
<<<
{email_text}
>>>"""
