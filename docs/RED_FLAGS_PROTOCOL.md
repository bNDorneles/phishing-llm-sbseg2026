# Protocolo de Red Flags

O projeto usa uma lista canonica e congelada de red flags para evitar redundancia metodologica na comparacao entre modelos.

## Papel da Calibracao

A calibracao usa 10 emails e serve para validar:

- prompt;
- parser JSON;
- logs;
- nomes das red flags;
- consistencia da saida vetorial.

Ela nao deve entrar nas metricas principais do artigo. A comparacao final usa os 90 emails de avaliacao.

## Lista Canonica

As colunas canonicas ficam em:

```text
src/red_flags.py
```

Durante a normalizacao, respostas com nomes antigos ou sinonimos conhecidos sao mapeadas para as colunas canonicas. Exemplos:

- `remetente_falsificado` vira `remetente_suspeito`;
- `anexos_estranhos` vira `anexos_suspeitos`.

Isso preserva rastreabilidade sem inflar artificialmente o vetor de features.

## Comandos do Protocolo Atual

Preparar os 100 emails:

```powershell
python scripts\prepare_small_protocol.py --seed 2026 --total-size 100 --calibration-size 10
```

Rodar calibracao:

```powershell
python scripts\run_experiment.py --dataset data\processed\phishing_calibration_10_seed2026.csv --models groq-llama-3-3-70b groq-qwen3-32b groq-compound groq-gpt-oss-120b --run-id calibracao_redflags_v1 --max-email-chars 3000
```

Rodar avaliacao:

```powershell
python scripts\run_experiment.py --dataset data\processed\phishing_eval_90_seed2026.csv --models groq-gpt-oss-120b groq-llama-3-3-70b groq-qwen3-32b groq-compound --run-id comparacao_100_seed_v1 --max-email-chars 3000
```

Reconstruir resultados e figuras:

```powershell
python scripts\rebuild_comparison_artifacts.py --run-id comparacao_100_seed_v1
```

## Interpretacao

As red flags devem ser lidas como sinais estruturados reportados pelo modelo. Elas ajudam a discutir padroes de decisao e erros, mas nao provam causalidade nem revelam o raciocinio interno do LLM.
