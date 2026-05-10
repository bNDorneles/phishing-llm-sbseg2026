# Troubleshooting

## 429 Too Many Requests

A Groq limitou requisicoes, tokens ou cota diaria.

Solucoes:

- rode um modelo por vez;
- continue com `--resume`;
- reduza `--max-email-chars` para modelos que estouram payload/token;
- aguarde a janela de limite indicada no log;
- revise cota e plano da Groq;
- aumente `groq_rate_limit_safety_factor` em `config/experiment.yaml` se houver 429 recorrente.

O pipeline usa backoff com jitter e respeita headers como `retry-after`, `x-ratelimit-reset-tokens` e `x-ratelimit-reset-requests`.

Observacao sobre `groq/compound`: ele pode rotear internamente para outros modelos. Se aparecer uma mensagem de 429 citando outro `model`, isso ainda pode vir da chamada do Compound. Para o artigo, mantenha o Compound fora das figuras finais ate ele fechar 90 respostas com `status=success`.

## Continuar uma Rodada

O pipeline salva `results/<run_id>/results_<modelo>.csv` incrementalmente. Se o terminal for interrompido:

```powershell
python scripts\run_experiment.py --dataset data\processed\phishing_eval_90_seed2026.csv --models groq-compound --run-id comparacao_100_seed_v1 --max-email-chars 1000 --resume
```

Depois reconstrua os artefatos:

```powershell
python scripts\rebuild_comparison_artifacts.py --run-id comparacao_100_seed_v1
```

## API Key Invalida

Sintomas comuns: `401 Unauthorized`, `403 Forbidden` ou mensagem de autenticacao.

Solucoes:

- confira se `.env` existe;
- confirme se a chave foi copiada sem espacos;
- verifique se a chave pertence a Groq;
- abra um novo terminal apos editar `.env`.

## `GROQ_API_KEY` Nao Encontrada

Solucoes:

- crie `.env` na raiz do projeto;
- confira se o arquivo se chama exatamente `.env`;
- deixe uma linha como `GROQ_API_KEY=sua_chave`;
- como alternativa temporaria no PowerShell, execute `$env:GROQ_API_KEY="sua_chave"`;
- rode comandos a partir da raiz do projeto.

## Modelo Nao Encontrado

Solucoes:

- revise `model_id` em `config/models.yaml`;
- confirme se o modelo esta disponivel na sua conta;
- teste outro modelo Groq;
- confira a documentacao da Groq antes da rodada completa.

## JSON Invalido Retornado por LLM

O pipeline tenta extrair JSON mesmo quando o modelo envolve a resposta em texto ou Markdown. Se ainda falhar:

- rode um teste pequeno;
- revise `parse_errors.csv`;
- revise `raw_responses/`;
- mantenha o schema do prompt estavel.

Quando a Groq retorna `json_validate_failed` no modo JSON estrito, o pipeline tenta uma segunda chamada sem `response_format` e usa o parser local.

## Verificar Cobertura

Confira:

```text
results/<run_id>/batch_summary_<modelo>.json
results/<run_id>/rebuild_manifest.json
```

No paper, use apenas modelos com 90 sucessos na avaliacao principal.

## Matplotlib ou SHAP Nao Instalado

```powershell
python -m pip install -r requirements.txt
```

Depois rode novamente a reconstrucao de artefatos.

## Dataset Nao Encontrado

Solucoes:

- coloque `Phishing_Email.csv` em `data/raw/`;
- ou coloque `Phishing_Email.csv.zip` em `data/raw/`;
- ou informe um caminho externo com `--zip-path`;
- rode o script de preparacao indicado em `docs/EXPERIMENTS.md`.
