from __future__ import annotations

import json

from src.red_flags import RED_FLAGS


SYSTEM_PROMPT = """Voce e um avaliador academico de seguranca cibernetica especializado em phishing.
Analise o email com criterio consistente. Responda apenas JSON valido, sem markdown."""


def build_user_prompt(email_text: str) -> str:
    flags = "\n".join(f"- {flag}" for flag in RED_FLAGS)
    schema = {
        "classification": "phishing ou safe",
        "probability": "numero entre 0 e 1 representando probabilidade de phishing",
        "red_flags": {flag: 0 for flag in RED_FLAGS},
        "scores": {
            "risco_geral": "inteiro 0 a 10",
            "confianca": "inteiro 0 a 10",
            "urgencia": "inteiro 0 a 10",
            "solicitacao_sensivel": "inteiro 0 a 10",
            "suspeita_links": "inteiro 0 a 10",
        },
        "explanation": "explicacao curta em uma frase",
    }
    return f"""Classifique o email abaixo como phishing ou safe e identifique red flags.

Red flags aceitas:
{flags}

Regras:
- Use 1 quando a red flag estiver presente e 0 quando estiver ausente.
- Nao invente campos fora do schema.
- A resposta deve ser JSON valido.
- A classificacao deve ser exatamente "phishing" ou "safe".

Schema esperado:
{json.dumps(schema, ensure_ascii=False, indent=2)}

EMAIL:
\"\"\"{email_text}\"\"\""""

