# Troubleshooting

## 429 Too Many Requests

A Groq limitou requisicoes ou cota.

Solucoes:

- reduza `--limit`;
- rode um modelo por vez;
- aguarde alguns minutos;
- revise cota e plano da Groq;
- aumente `retry_sleep_seconds` em `config/experiment.yaml`.

## API Key Invalida

Sintomas comuns: `401 Unauthorized`, `403 Forbidden` ou mensagem de autenticacao.

Solucoes:

- confira se `.env` existe;
- confirme se a chave foi copiada sem espacos;
- verifique se a chave pertence a Groq;
- abra um novo terminal apos editar `.env`.

## Modelo Nao Encontrado

Sintomas comuns: `404`, `model not found` ou erro de modelo indisponivel.

Solucoes:

- revise `model_id` em `config/models.yaml`;
- confirme se o modelo esta disponivel na sua conta;
- teste outro modelo Groq;
- confira a documentacao da Groq antes da rodada completa.

## JSON Invalido Retornado por LLM

O pipeline tenta extrair JSON mesmo quando o modelo envolve a resposta em texto ou markdown. Se ainda falhar:

- reduza `temperature` para `0.0`;
- rode um teste pequeno com `--limit 5`;
- revise arquivos em `results/<run_id>/parse_errors.csv`;
- revise a resposta bruta em `results/<run_id>/raw_responses/`;
- reforce o prompt em `src/prompts.py`, mantendo o mesmo schema.

## Matplotlib ou SHAP Nao Instalado

Se dependencias opcionais faltarem, o pipeline cria arquivos como:

```text
plots_skipped.txt
shap/shap_skipped.txt
```

Solucoes:

```powershell
python -m pip install -r requirements.txt
```

Depois rode novamente o experimento.

## Dataset Nao Encontrado

Sintomas comuns: `FileNotFoundError` para `Phishing_Email.csv`.

Solucoes:

- coloque `Phishing_Email.csv` em `data/raw/`;
- ou coloque `Phishing_Email.csv.zip` em `data/raw/`;
- ou informe um caminho externo com `--zip-path`;
- rode:

```powershell
python scripts\prepare_dataset.py
```
