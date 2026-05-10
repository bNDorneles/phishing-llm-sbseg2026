# Setup

Este guia prepara o ambiente local para executar o pipeline.

## 1. Criar Ambiente Virtual

```powershell
cd phishing-llm-sbseg2026
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se `python` nao estiver no PATH:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 2. Instalar Dependencias

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Criar `.env`

```powershell
copy .env.example .env
```

## 4. Configurar Chaves

Edite `.env` localmente:

```env
GROQ_API_KEY=
GROQ_MODELS=groq-gpt-oss-120b,groq-llama-3-3-70b,groq-compound,groq-qwen3-32b
LLM_MAX_ATTEMPTS=3
LLM_REQUEST_TIMEOUT_SECONDS=90
LLM_BACKOFF_BASE_SECONDS=1
LLM_BACKOFF_MAX_SECONDS=30
GROQ_RATE_LIMIT_SAFETY_FACTOR=1.2
GROQ_MIN_REMAINING_TOKENS=0
LLM_SLEEP_BETWEEN_REQUESTS_SECONDS=0
```

O arquivo `.env` e ignorado pelo Git.

O backoff, timeout e controle de rate limit tambem possuem valores em `config/experiment.yaml`. Quando preenchidas no `.env`, as variaveis acima sobrescrevem os valores padrao.

## 5. Preparar Dataset

Adicione manualmente o dataset em:

```text
data/raw/Phishing_Email.csv
```

Ou deixe o ZIP local em:

```text
data/raw/Phishing_Email.csv.zip
```

Depois execute:

```powershell
python scripts\prepare_dataset.py
```

Tambem e possivel informar um caminho externo:

```powershell
python scripts\prepare_dataset.py --zip-path caminho/para/Phishing_Email.csv.zip
```

O script remove textos vazios, normaliza labels e gera a amostra oficial em `data/processed/`.
