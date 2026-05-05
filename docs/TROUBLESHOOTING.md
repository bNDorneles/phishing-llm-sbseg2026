# Troubleshooting

## 429 Too Many Requests

A Groq limitou requisicoes ou cota.

Solucoes:

- reduza `--limit`;
- rode um modelo por vez;
- aguarde alguns minutos;
- revise cota e plano da Groq;
- aumente `groq_rate_limit_safety_factor` em `config/experiment.yaml` se ainda houver 429 em execucoes longas.

O pipeline usa exponential backoff com full jitter para falhas transientes.

Ele tambem respeita os headers oficiais da Groq:

- `retry-after`;
- `x-ratelimit-remaining-tokens`;
- `x-ratelimit-reset-tokens`;
- `x-ratelimit-remaining-requests`;
- `x-ratelimit-reset-requests`.

Se ainda houver 429 em execucoes longas, use apenas um modelo por vez ou aumente `groq_rate_limit_safety_factor`.

Observacao sobre `groq/compound`: ele pode rotear internamente para outros modelos. Se aparecer uma mensagem de 429 citando outro `model`, o pipeline usa uma cadencia conservadora e tenta respeitar mensagens do corpo da resposta, como `Please try again in 705ms`. Para a rodada final de 1009 emails, prefira rodar um modelo por vez se sua cota da Groq estiver baixa.

Se o limite for diario, a amostra de 1009 pode ultrapassar contas com RPD de 1000. Nesse caso, use o mesmo `--run-id` com `--resume` no dia seguinte:

```powershell
python scripts\run_experiment.py --models groq-gpt-oss-120b --run-id final_1009_gpt_oss_120b --resume
```

## API Key Invalida

Sintomas comuns: `401 Unauthorized`, `403 Forbidden` ou mensagem de autenticacao.

Solucoes:

- confira se `.env` existe;
- confirme se a chave foi copiada sem espacos;
- verifique se a chave pertence a Groq;
- abra um novo terminal apos editar `.env`.

## `GROQ_API_KEY` Nao Encontrada

Se aparecer `KeyError: 'GROQ_API_KEY'` ou mensagem dizendo que `GROQ_API_KEY` nao foi encontrada, a chamada ainda nao chegou na Groq. O problema esta no carregamento da variavel local.

Solucoes:

- crie `.env` na raiz do projeto;
- confira se o arquivo se chama exatamente `.env`, sem `.txt` no final;
- deixe uma linha como `GROQ_API_KEY=sua_chave`;
- como alternativa temporaria no PowerShell, execute `$env:GROQ_API_KEY="sua_chave"` antes de rodar o experimento;
- rode o comando a partir da raiz do projeto.

## Modelo Nao Encontrado

Sintomas comuns: `404`, `model not found` ou erro de modelo indisponivel.

Solucoes:

- revise `model_id` em `config/models.yaml`;
- confirme se o modelo esta disponivel na sua conta;
- teste outro modelo Groq;
- confira a documentacao da Groq antes da rodada completa.

## JSON Invalido Retornado por LLM

O pipeline tenta extrair JSON mesmo quando o modelo envolve a resposta em texto ou markdown. Se ainda falhar:

- reduza `temperature` para `0.0`;
- rode um teste pequeno com `--limit 5`;
- revise arquivos em `results/<run_id>/parse_errors.csv`;
- revise a resposta bruta em `results/<run_id>/raw_responses/`;
- reforce o prompt em `src/prompts.py`, mantendo o mesmo schema.

Quando a Groq retorna `json_validate_failed` no modo JSON estrito, o erro aparece como `json_mode_validation`. O pipeline agora tenta automaticamente uma segunda chamada sem `response_format` e usa o parser local para extrair o JSON. Se mesmo assim houver falha, a linha fica com `status=failed`, sem interromper o lote.

## Verificar Cobertura

Se quiser confirmar que nenhum e-mail ficou sem status final, confira:

```text
results/<run_id>/batch_summary_<modelo>.json
```

O campo `coverage_ok` deve ser `true`.

## Matplotlib ou SHAP Nao Instalado

Se dependencias opcionais faltarem, o pipeline cria arquivos como:

```text
plots_skipped.txt
shap/shap_skipped.txt
```

Solucoes:

```powershell
python -m pip install -r requirements.txt
```

Depois rode novamente o experimento.

## Dataset Nao Encontrado

Sintomas comuns: `FileNotFoundError` para `Phishing_Email.csv`.

Solucoes:

- coloque `Phishing_Email.csv` em `data/raw/`;
- ou coloque `Phishing_Email.csv.zip` em `data/raw/`;
- ou informe um caminho externo com `--zip-path`;
- rode:

```powershell
python scripts\prepare_dataset.py
```
