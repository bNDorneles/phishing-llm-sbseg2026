# phishing-llm-sbseg2026

Pipeline reprodutivel para comparar Large Language Models (LLMs) na deteccao de phishing em emails, com foco em uma submissao academica ao SBSeg.

## Objetivo

O projeto avalia se LLMs recentes conseguem classificar emails como `phishing` ou `safe` e, ao mesmo tempo, registrar red flags explicaveis que apoiem a analise dos erros. A contribuicao esperada nao e um produto de deteccao em producao, mas um protocolo experimental rastreavel para discutir desempenho, cobertura, falsos positivos, falsos negativos e sinais linguisticos/comportamentais em emails de phishing.

## Protocolo Principal

A comparacao principal usa o run:

```text
results/comparacao_100_seed_v1/
```

O protocolo tem 100 emails no total:

- 10 emails de calibracao tecnica, usados para validar prompt, red flags, parser e logs;
- 90 emails de avaliacao, usados nas metricas principais do artigo.

A calibracao nao e misturada nas metricas comparativas. Ela deve aparecer no artigo como etapa metodologica separada. A comparacao final so deve incluir modelos com 90 respostas validas na avaliacao.

## Modelos Comparados

Modelos configurados via Groq:

| ID local | Modelo Groq |
|---|---|
| `groq-gpt-oss-120b` | `openai/gpt-oss-120b` |
| `groq-llama-3-3-70b` | `llama-3.3-70b-versatile` |
| `groq-qwen3-32b` | `qwen/qwen3-32b` |
| `groq-compound` | `groq/compound` |

O `groq/compound` pode acionar modelos internos e sofrer limites de cota diferentes dos demais. Por isso, ele deve entrar nas figuras finais apenas quando atingir 90 sucessos na rodada principal.

## Estrutura

```text
phishing-llm-sbseg2026/
  config/       # configuracoes de modelos e experimento
  data/         # dados locais; datasets grandes nao sao versionados
  docs/         # documentacao operacional e metodologica
  paper/        # notas e contexto para escrita do artigo
  reports/      # relatorios Markdown gerados
  results/      # saidas locais das rodadas experimentais
  scripts/      # preparacao, execucao e reconstrucao de artefatos
  src/          # codigo do pipeline
```

Rodadas antigas ou exploratorias devem ficar em `results/_archive/`. O run `comparacao_100_seed_v1` e a referencia local para o paper.

## Instalacao

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copie o arquivo de ambiente e informe a chave da Groq:

```powershell
copy .env.example .env
```

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

Nunca versionar `.env`, datasets brutos, resultados completos ou respostas brutas.

## Preparar o Protocolo de 100 Emails

```powershell
python scripts\prepare_small_protocol.py --seed 2026 --total-size 100 --calibration-size 10
```

Arquivos esperados:

```text
data/processed/phishing_calibration_10_seed2026.csv
data/processed/phishing_eval_90_seed2026.csv
```

## Rodar Calibracao

```powershell
python scripts\run_experiment.py --dataset data\processed\phishing_calibration_10_seed2026.csv --models groq-llama-3-3-70b groq-qwen3-32b groq-compound groq-gpt-oss-120b --run-id calibracao_redflags_v1 --max-email-chars 3000
```

## Rodar Comparacao Principal

```powershell
python scripts\run_experiment.py --dataset data\processed\phishing_eval_90_seed2026.csv --models groq-gpt-oss-120b groq-llama-3-3-70b groq-qwen3-32b groq-compound --run-id comparacao_100_seed_v1 --max-email-chars 3000
```

Para continuar sem refazer sucessos:

```powershell
python scripts\run_experiment.py --dataset data\processed\phishing_eval_90_seed2026.csv --models groq-compound --run-id comparacao_100_seed_v1 --max-email-chars 1000 --resume
```

## Reconstruir Resultados e Figuras do Paper

Depois de uma rodada, regenere os artefatos sem chamar a API:

```powershell
python scripts\rebuild_comparison_artifacts.py --run-id comparacao_100_seed_v1
```

Esse comando:

- le os arquivos `results_<modelo>.csv`;
- inclui apenas modelos com pelo menos 90 sucessos;
- reconstrui `final_results.csv`;
- recalcula `metrics_by_model.csv`;
- atualiza `false_positives.csv`, `false_negatives.csv` e `parse_errors.csv`;
- cria PNGs academicos em `results/comparacao_100_seed_v1/plots_paper/`;
- preserva os PNGs antigos em `results/comparacao_100_seed_v1/plots/`.

Para diagnostico, existe `--allow-partial`, mas ele nao deve ser usado para as figuras principais do artigo.

## Saidas Principais

Em `results/comparacao_100_seed_v1/`:

- `results_<modelo>.csv`: saida individual de cada modelo;
- `final_results.csv`: consolidado apenas com modelos aptos ao comparativo final;
- `metrics_by_model.csv`: metricas de classificacao;
- `red_flag_frequency.csv`: frequencia media das red flags;
- `plots/`: graficos antigos preservados;
- `plots_paper/`: graficos novos, legiveis e adequados ao artigo;
- `rebuild_manifest.json`: registro de quais modelos entraram ou ficaram fora.

## Interpretacao

As metricas usam `phishing` como classe positiva:

- `precision`: entre alertas de phishing, quantos eram phishing de fato;
- `recall`: entre phishing reais, quantos foram detectados;
- `specificity`: entre emails seguros, quantos foram preservados como seguros;
- `f1`: equilibrio entre precision e recall;
- `false_negative_rate`: phishing que passou como seguro, erro mais critico para seguranca.

Falhas de API, parser ou limite de cota nao devem ser escondidas. Elas ficam registradas nos CSVs individuais e no manifesto de reconstrucao. Quando um modelo nao fecha 90 sucessos, ele fica fora do comparativo principal ate a rodada ser completada.

## Artigo

O arquivo `paper/contexto_artigo_sbseg2026.md` concentra o contexto para escrita assistida no PRISMA/ChatGPT. Ele deve ser usado como guia para formular o artigo sem inventar resultados alem dos CSVs disponiveis.
