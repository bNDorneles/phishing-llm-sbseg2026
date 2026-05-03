# Reports

Esta pasta recebe relatorios Markdown gerados automaticamente pelo pipeline.

Os relatorios finais podem ser recriados executando:

```powershell
python scripts\run_experiment.py --models mock --limit 20 --run-id smoke_mock_20
```

Arquivos como `CHANGELOG_EXPERIMENTOS.md`, `07_metricas_resultados.md`, `08_analise_red_flags.md`, `09_analise_shap.md`, `10_analise_erros.md` e `11_limitacoes.md` sao artefatos gerados. Eles nao precisam ser versionados para que o experimento seja reproduzido.

