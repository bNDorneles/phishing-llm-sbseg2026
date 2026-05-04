# Experiments

Este documento lista comandos comuns para executar experimentos.

Modelos Groq configurados em `config/models.yaml`:

- `groq-llama-3-1-8b`
- `groq-llama-3-3-70b`
- `groq-llama-4-scout`
- `groq-qwen3-32b`

## Mock Local

Valida o pipeline sem custo e sem API key:

```powershell
python scripts\run_experiment.py --models mock --limit 20 --run-id smoke_mock_20
```

## Groq com 20 Amostras

```powershell
python scripts\run_experiment.py --models groq-llama-3-1-8b --limit 20
```

## Groq com 100 Amostras

```powershell
python scripts\run_experiment.py --models groq-llama-3-1-8b --limit 100
```

## Groq com 1009 Amostras

```powershell
python scripts\run_experiment.py --models groq-llama-3-1-8b
```

## Multiplos Modelos Groq

```powershell
python scripts\run_experiment.py --models groq-llama-3-1-8b groq-llama-3-3-70b groq-llama-4-scout groq-qwen3-32b
```

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
- `raw_responses/`
- `plots/`
- `shap/`

Relatorios consolidados sao atualizados em:

```text
reports/
```
