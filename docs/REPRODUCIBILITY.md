# Reprodutibilidade

Este projeto foi organizado para repetir a comparacao principal sem misturar calibracao, avaliacao e rodadas exploratorias.

## Protocolo Principal

- Run: `comparacao_100_seed_v1`.
- Total metodologico: 100 emails.
- Calibracao tecnica: 10 emails.
- Avaliacao comparativa: 90 emails.
- Classe positiva: `phishing`.
- Prompt padronizado em `src/prompts.py`.
- Red flags canonicas em `src/red_flags.py`.
- Configuracoes em `config/experiment.yaml` e `config/models.yaml`.

A calibracao valida o aparato experimental e nao entra nas metricas principais. O comparativo final deve incluir apenas modelos com 90 respostas validas na avaliacao.

## Arquivos de Referencia

CSV individual por modelo:

```text
results/comparacao_100_seed_v1/results_<modelo>.csv
```

Consolidado reconstruido:

```text
results/comparacao_100_seed_v1/final_results.csv
```

Manifesto de inclusao/exclusao:

```text
results/comparacao_100_seed_v1/rebuild_manifest.json
```

## Reconstrucao

Para recriar metricas, relatorios e PNGs academicos sem chamar API:

```powershell
python scripts\rebuild_comparison_artifacts.py --run-id comparacao_100_seed_v1
```

O script exige 90 sucessos por modelo. Modelos incompletos permanecem preservados nos CSVs individuais, mas ficam fora de `final_results.csv` e das figuras principais.

## Respostas Brutas

Respostas dos LLMs ficam localmente em:

```text
results/<run_id>/raw_responses/
```

Esses arquivos nao devem ser versionados porque podem conter textos longos, dados sensiveis e saidas custosas de recriar.

## Cobertura do Lote

Cada linha processada registra:

- `status`: `success` ou `failed`;
- `request_id`: identificador correlacionavel nos logs;
- `email_hash`: hash curto do conteudo;
- `attempts`: tentativas usadas;
- `latency_seconds`: latencia total;
- `error_type`: tipo de falha, quando houver.

Cada modelo tambem gera `batch_summary_<modelo>.json`.

## Como Repetir

1. Usar o mesmo dataset processado de avaliacao.
2. Manter as configuracoes do experimento.
3. Rodar com o mesmo `run-id`.
4. Usar `--resume` para completar apenas pendentes/falhas.
5. Reconstruir artefatos com `scripts\rebuild_comparison_artifacts.py`.

Execucoes via API podem variar por mudancas de modelo, cota, infraestrutura ou politicas internas do provedor. Por isso, respostas brutas, logs e manifestos devem ser preservados localmente.
