from __future__ import annotations

import json

from src.red_flags import RED_FLAG_DEFINITIONS, RED_FLAGS


SYSTEM_PROMPT = """Voce e um avaliador academico de seguranca cibernetica especializado em phishing.
Analise o email com criterio consistente. Responda apenas JSON valido, sem markdown."""


def build_user_prompt(email_text: str) -> str:
    flags = json.dumps(RED_FLAGS, ensure_ascii=False)
    definitions = json.dumps(RED_FLAG_DEFINITIONS, ensure_ascii=False, separators=(",", ":"))
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
Use apenas a lista canonica abaixo. Nao crie red flags novas, sinonimos ou duplicadas.
Se dois sinais forem equivalentes, marque apenas a red flag canonica correspondente.
Red flags: {flags}
Definicoes canonicas: {definitions}
Schema: {json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}
Email:
<<<
{email_text}
>>>"""


def build_compact_user_prompt(email_text: str) -> str:
    flags = json.dumps(RED_FLAGS, ensure_ascii=False)
    return (
        "Classifique o email como phishing ou safe. "
        "Retorne somente JSON minificado com as chaves: classification, probability, red_flags, scores, explanation. "
        "classification deve ser phishing ou safe. probability deve ser numero entre 0 e 1. "
        f"red_flags deve conter exatamente estas chaves com valores 0 ou 1: {flags}. "
        "scores deve conter risco_geral, confianca, urgencia, solicitacao_sensivel, suspeita_links de 0 a 10. "
        "explanation deve ter no maximo 120 caracteres. "
        f"Email:\n<<<\n{email_text}\n>>>"
    )
