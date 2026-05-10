# Experimentos

Este documento registra o protocolo experimental recomendado para o artigo SBSeg e comandos de reproducao.

## Protocolo Principal: 100 Emails

O protocolo principal tem 100 emails no total:

- 10 emails de calibracao tecnica;
- 90 emails de avaliacao comparativa.

As chamadas de LLM sao independentes e sem memoria. Portanto, a calibracao serve para validar prompt, parser, red flags e logs; ela nao treina os modelos e nao deve entrar nas metricas principais. O artigo deve comparar os modelos somente sobre os 90 emails de avaliacao.

Run principal:

```text
results/comparacao_100_seed_v1/
```

## Preparacao dos Dados

```powershell
python scripts\prepare_small_protocol.py --seed 2026 --total-size 100 --calibration-size 10
```

Saidas esperadas:

```text
data\processed\phishing_calibration_10_seed2026.csv
data\processed\phishing_eval_90_seed2026.csv
```

## Calibracao

```powershell
python scripts\run_experiment.py --dataset data\processed\phishing_calibration_10_seed2026.csv --models groq-llama-3-3-70b groq-qwen3-32b groq-compound groq-gpt-oss-120b --run-id calibracao_redflags_v1 --max-email-chars 3000
```

Use a calibracao para conferir:

- se o JSON esta sendo parseado;
- se as red flags estao coerentes;
- se os logs preservam rastreabilidade;
- se a chave e os limites da Groq estao funcionando.

## Comparacao de 90 Emails

```powershell
python scripts\run_experiment.py --dataset data\processed\phishing_eval_90_seed2026.csv --models groq-gpt-oss-120b groq-llama-3-3-70b groq-qwen3-32b groq-compound --run-id comparacao_100_seed_v1 --max-email-chars 3000
```

Se a execucao parar por limite, continuar com o mesmo `run-id`:

```powershell
python scripts\run_experiment.py --dataset data\processed\phishing_eval_90_seed2026.csv --models groq-compound --run-id comparacao_100_seed_v1 --max-email-chars 1000 --resume
```

O `groq/compound` pode acionar modelos internos e retornar 429 para modelos que nao aparecem diretamente no comando. Para o artigo, ele so entra no comparativo final quando tiver 90 respostas com `status=success`.

## Reconstrucao de Artefatos

Recalcular metricas, consolidar CSVs individuais e gerar figuras academicas:

```powershell
python scripts\rebuild_comparison_artifacts.py --run-id comparacao_100_seed_v1
```

Comportamento padrao:

- le `results_<modelo>.csv`;
- exige 90 sucessos por modelo;
- exclui modelos incompletos do `final_results.csv`;
- preserva os CSVs individuais;
- gera figuras novas em `plots_paper/`;
- preserva figuras antigas em `plots/`;
- grava `rebuild_manifest.json`.

Para diagnosticar um modelo incompleto:

```powershell
python scripts\rebuild_comparison_artifacts.py --run-id comparacao_100_seed_v1 --allow-partial
```

Nao usar `--allow-partial` para figuras principais do artigo.

## Modelos

| ID local | Modelo Groq |
|---|---|
| `groq-gpt-oss-120b` | `openai/gpt-oss-120b` |
| `groq-llama-3-3-70b` | `llama-3.3-70b-versatile` |
| `groq-qwen3-32b` | `qwen/qwen3-32b` |
| `groq-compound` | `groq/compound` |

## Rodadas Maiores

Rodadas com cortes maiores devem ser tratadas como exploratorias nesta versao do projeto. Elas nao devem substituir a comparacao principal, a menos que seja definido um corte justo entre pelo menos dois modelos com o mesmo numero de emails avaliados.

Diretriz para o paper atual:

- resultado central: comparacao dos modelos no protocolo de 90 emails avaliativos;
- calibracao: descrita como etapa metodologica;
- rodadas maiores: material secundario ou trabalho futuro, se ainda nao houver corte justo.

## Smoke Test Local

Para validar o pipeline sem API:

```powershell
python scripts\run_experiment.py --models mock --limit 20 --run-id smoke_mock_20
```

## Saidas

Cada execucao cria ou atualiza:

```text
results/<run_id>/
```

Arquivos principais:

- `results_<modelo>.csv`
- `final_results.csv`
- `metrics_by_model.csv`
- `false_positives.csv`
- `false_negatives.csv`
- `parse_errors.csv`
- `batch_summary_<modelo>.json`
- `raw_responses/`
- `plots/`
- `plots_paper/`

Relatorios consolidados ficam em:

```text
reports/
```
