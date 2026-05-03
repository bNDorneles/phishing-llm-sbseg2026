# phishing-llm-sbseg2026

Pipeline reprodutivel para avaliacao comparativa de Large Language Models (LLMs) na deteccao de phishing em emails.

## Objetivo

Este projeto implementa um protocolo experimental para comparar LLMs na tarefa de classificar emails como `phishing` ou `safe`, extrair red flags, gerar um dataset vetorial, calcular metricas, produzir graficos, aplicar SHAP sobre um classificador Random Forest e gerar relatorios Markdown.

O foco do repositorio e pesquisa aplicada em ciberseguranca. Ele nao pretende propor um produto novo de deteccao de phishing, mas sim apoiar uma replicacao e atualizacao reprodutivel de um estudo academico anterior.

## Contexto Academico

O projeto parte de uma linha metodologica anterior sobre avaliacao de LLMs para deteccao de phishing, atualizando o protocolo experimental com modelos recentes, multiplos provedores e uma estrutura mais completa de reprodutibilidade. A proposta preserva a ideia central de comparar modelos sob um mesmo prompt, uma mesma amostra e as mesmas metricas, mas organiza uma nova versao do estudo para 2026.

Tambem sao reaproveitadas ideias tecnicas de trabalhos com fake news, apenas como base de engenharia experimental: pipeline com LLM, geracao de dataset, integracao com Python, Random Forest, SHAP e relatorios. O dominio final permanece phishing.

## Relacao com SBSeg 2026

Este repositorio foi estruturado como artefato de pesquisa para uma submissao ao SBSeg 2026. As principais preocupacoes sao:

- reprodutibilidade;
- separacao entre baseline historico e resultados novos;
- preservacao local de respostas brutas;
- rastreabilidade de configuracoes;
- seguranca no uso de API keys;
- documentacao clara para avaliadores e coautores.

## O Que o Projeto Faz

- Le `Phishing_Email.csv`.
- Remove emails vazios.
- Normaliza labels para `phishing` e `safe`.
- Gera amostra estratificada com seed fixa.
- Executa LLMs via Groq, OpenAI, Gemini, DeepSeek ou `mock`.
- Solicita resposta JSON padronizada.
- Extrai 20 red flags de phishing.
- Salva respostas brutas localmente.
- Gera `final_results.csv` com predicoes, red flags, scores, temperatura e modelo.
- Calcula accuracy, precision, recall, F1-score, TP, TN, FP e FN.
- Gera graficos e matrizes de confusao.
- Treina Random Forest sobre red flags e aplica SHAP.
- Atualiza relatorios Markdown automaticamente.

## Estrutura de Pastas

```text
phishing-llm-sbseg2026/
  config/              # YAMLs de experimento e modelos
  data/
    raw/               # dataset bruto local, nao versionado
    processed/         # amostras processadas locais, nao versionadas
    baseline_historico/# resultados historicos locais, nao versionados
  docs/                # documentacao operacional
  paper/               # notas metodologicas e rascunhos
  reports/             # relatorios gerados automaticamente
  results/             # outputs de execucao, nao versionados
  scripts/             # comandos de preparacao e execucao
  src/                 # codigo do pipeline
```

## Instalacao

Crie e ative um ambiente virtual:

```powershell
cd phishing-llm-sbseg2026
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se `python` nao estiver no PATH, tente:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Configuracao do `.env`

Copie o exemplo:

```powershell
copy .env.example .env
```

Preencha somente as chaves dos provedores que serao usados:

```env
GROQ_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
DEEPSEEK_API_KEY=
```

Nunca envie `.env` para o GitHub.

## Dados

O dataset nao e versionado neste repositorio. Baixe ou adicione manualmente `Phishing_Email.csv` em:

```text
data/raw/Phishing_Email.csv
```

Tambem e possivel usar o ZIP local esperado pelo script:

```text
data/raw/Phishing_Email.csv.zip
```

Prepare a amostra oficial:

```powershell
python scripts\prepare_dataset.py
```

Ou informe um caminho externo:

```powershell
python scripts\prepare_dataset.py --zip-path caminho/para/Phishing_Email.csv.zip
```

O script gera uma amostra de 1.009 emails com seed 42, composta por 602 emails safe e 407 emails phishing.

## Teste Pequeno

Use o modelo `mock` para validar o pipeline sem custo e sem chaves:

```powershell
python scripts\run_experiment.py --models mock --limit 20 --run-id smoke_mock_20
```

## Experimento Real

Habilite modelos em `config/models.yaml` alterando `enabled: false` para `enabled: true`, ou informe modelos explicitamente:

```powershell
python scripts\run_experiment.py --models groq-llama --limit 20
python scripts\run_experiment.py --models groq-llama openai-gpt gemini deepseek
```

Para a amostra oficial completa:

```powershell
python scripts\run_experiment.py --models groq-llama openai-gpt gemini deepseek
```

## Interpretacao dos Resultados

Cada execucao cria uma pasta em `results/<run_id>/` com:

- `final_results.csv`: saida vetorial completa.
- `metrics_by_model.csv`: accuracy, precision, recall, F1, TP, TN, FP e FN.
- `false_positives.csv`: emails safe classificados como phishing.
- `false_negatives.csv`: emails phishing classificados como safe.
- `raw_responses/`: respostas brutas locais por modelo e email.
- `plots/`: graficos de metricas, F1, matriz de confusao e red flags.
- `shap/`: importancia SHAP quando dependencias estao instaladas.

Os relatorios Markdown ficam em `reports/`.

## Rate Limit 429

Erro `429 Too Many Requests` indica limite de requisicoes ou cota do provedor. Solucoes recomendadas:

- reduzir `--limit` durante testes;
- rodar um modelo por vez;
- aumentar pausas e retries em `config/experiment.yaml`;
- verificar cota e plano do provedor;
- evitar repetir a amostra completa sem necessidade.

## Reproducibilidade

O protocolo principal usa:

- seed 42;
- amostra de 1.009 emails;
- 602 emails safe e 407 phishing;
- prompts versionados;
- red flags versionadas;
- respostas brutas preservadas localmente;
- resultados historicos separados em `data/baseline_historico/`.

Para repetir uma execucao, mantenha o mesmo dataset, o mesmo `config/experiment.yaml`, o mesmo `config/models.yaml` e o mesmo `run-id`.

## Proximos Passos

- Criar comparador automatico entre resultados historicos e resultados 2026.
- Adicionar controle de custo por provedor.
- Adicionar suporte a execucao em lotes com pausa entre requisicoes.
- Consolidar tabelas finais para o artigo.
- Criar pacote de artefatos anonimizados para submissao double blind.

## Aviso de Seguranca

Nunca suba `.env`, API keys, tokens, logs com segredo, datasets privados ou respostas brutas sensiveis. Antes de publicar, execute uma busca por chaves e revise `git status`.

## Aviso de Dados

Datasets grandes, arquivos `.csv`, ZIPs, resultados reais e respostas brutas nao devem ser versionados. Eles devem ser baixados/adicionados manualmente em `data/raw/` e recriados pelo pipeline.
