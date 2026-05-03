# Experiments

Este documento lista comandos comuns para executar experimentos.

## Mock Local

Valida o pipeline sem custo e sem API key:

```powershell
python scripts\run_experiment.py --models mock --limit 20 --run-id smoke_mock_20
```

## Groq com 20 Amostras

```powershell
python scripts\run_experiment.py --models groq-llama --limit 20
```

## Groq com 100 Amostras

```powershell
python scripts\run_experiment.py --models groq-llama --limit 100
```

## Groq com 1009 Amostras

```powershell
python scripts\run_experiment.py --models groq-llama
```

## Multiplos Modelos

```powershell
python scripts\run_experiment.py --models groq-llama openai-gpt gemini deepseek
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

