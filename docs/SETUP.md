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
```

O arquivo `.env` e ignorado pelo Git.

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
