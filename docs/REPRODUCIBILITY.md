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

## Respostas Brutas

As respostas brutas dos LLMs sao preservadas localmente em:

```text
results/<run_id>/raw_responses/
```

Esses arquivos nao sao versionados, pois podem conter dados sensiveis, custos altos para recriar e saidas longas dos provedores.

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

Para provedores remotos, pequenas variacoes ainda podem ocorrer por mudancas de modelo, infraestrutura do provedor ou politicas internas da API.

