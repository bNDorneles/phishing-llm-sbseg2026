# Reproducibility

Este projeto foi estruturado para permitir repeticao controlada dos experimentos.

## Protocolo Principal

- Seed fixa: `42`.
- Tamanho da amostra: `1009`.
- Proporcao da amostra: `602 safe / 407 phishing`.
- Labels normalizados: `safe` e `phishing`.
- Prompt padronizado em `src/prompts.py`.
- Red flags padronizadas em `src/red_flags.py`.
- Configuracoes em `config/experiment.yaml` e `config/models.yaml`.
- Validacao por modelo: `total_entrada == total_processado_sucesso + total_processado_falha`.
- Ritmo de chamadas Groq baseado nos limites oficiais de RPM/TPM por modelo e nos headers retornados pela API.

## Respostas Brutas

As respostas brutas dos LLMs sao preservadas localmente em:

```text
results/<run_id>/raw_responses/
```

Esses arquivos nao sao versionados, pois podem conter dados sensiveis, custos altos para recriar e saidas longas dos modelos.

## Cobertura do Lote

Cada e-mail processado recebe uma linha em `final_results.csv` com:

- `status`: `success` ou `failed`;
- `request_id`: identificador correlacionavel nos logs;
- `email_hash`: hash curto do conteudo, sem expor o texto completo;
- `attempts`: tentativas usadas;
- `latency_seconds`: latencia total;
- `error_type`: tipo de falha, quando houver.

Cada modelo gera tambem `batch_summary_<modelo>.json`, com a validacao formal de cobertura.

## Como Repetir uma Execucao

1. Use o mesmo `Phishing_Email.csv`.
2. Mantenha `config/experiment.yaml` inalterado.
3. Mantenha os mesmos modelos em `config/models.yaml`.
4. Execute novamente com o mesmo comando.

Exemplo:

```powershell
python scripts\prepare_dataset.py
python scripts\run_experiment.py --models mock --limit 20 --run-id smoke_mock_20
```

Para execucoes via Groq, pequenas variacoes ainda podem ocorrer por mudancas de modelo, infraestrutura da API ou politicas internas do servico.
