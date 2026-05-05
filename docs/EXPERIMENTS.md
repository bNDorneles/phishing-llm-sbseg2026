# Experiments

Este documento lista comandos comuns para executar experimentos.

Modelos Groq configurados em `config/models.yaml`:

- `groq-gpt-oss-120b`
- `groq-llama-3-3-70b`
- `groq-compound`
- `groq-qwen3-32b`

## Mock Local

Valida o pipeline sem custo e sem API key:

```powershell
python scripts\run_experiment.py --models mock --limit 20 --run-id smoke_mock_20
```

## Groq com 20 Amostras

```powershell
python scripts\run_experiment.py --models groq-gpt-oss-120b --limit 20
```

## Groq com 100 Amostras

```powershell
python scripts\run_experiment.py --models groq-gpt-oss-120b --limit 100
```

## Groq com 1009 Amostras

```powershell
python scripts\run_experiment.py --models groq-gpt-oss-120b
```

Para reduzir risco de 429 em contas com cota baixa, rode a amostra de 1009 um modelo por vez:

```powershell
python scripts\run_experiment.py --models groq-llama-3-3-70b --run-id final_1009_llama_70b
python scripts\run_experiment.py --models groq-gpt-oss-120b --run-id final_1009_gpt_oss_120b
python scripts\run_experiment.py --models groq-qwen3-32b --run-id final_1009_qwen3_32b
```

Se o limite diario encerrar a rodada antes do fim, repita o mesmo comando com `--resume` depois do reset da cota:

```powershell
python scripts\run_experiment.py --models groq-gpt-oss-120b --run-id final_1009_gpt_oss_120b --resume
```

## Multiplos Modelos Groq

```powershell
python scripts\run_experiment.py --models groq-gpt-oss-120b groq-llama-3-3-70b groq-compound groq-qwen3-32b
```

`groq/compound` fica disponivel para comparacao, mas pode acionar modelos internos e gerar 429 citando outro `model_id`. Use-o como rodada separada se quiser preservar a execucao principal.

## Outputs

Cada execucao cria:

```text
results/<run_id>/
```

Arquivos principais:

- `final_results.csv`
- `metrics_by_model.csv`
- `false_positives.csv`
- `false_negatives.csv`
- `parse_errors.csv`
- `batch_summary_<modelo>.json`
- `raw_responses/`
- `plots/`
- `shap/`

Relatorios consolidados sao atualizados em:

```text
reports/
```

## Regenerar Graficos sem Chamar a API

Se uma execucao ja possui `results/<run_id>/final_results.csv`, voce pode recriar metricas, graficos e relatorios sem fazer novas chamadas aos modelos:

```powershell
python scripts\regenerate_artifacts.py --run-id nome_da_execucao --skip-shap
```

## Selecionar Modelos por `.env`

Tambem e possivel definir modelos no `.env`:

```env
GROQ_MODELS=groq-gpt-oss-120b,groq-llama-3-3-70b
```

Depois rode:

```powershell
python scripts\run_experiment.py --limit 20 --run-id teste_env_models
```
