# Contexto para Escrita do Artigo SBSeg

Use este arquivo como briefing para escrever o artigo no PRISMA/ChatGPT. Nao inventar resultados, numeros, rankings ou conclusoes que nao estejam nos CSVs e relatorios gerados em `results/comparacao_100_seed_v1/`.

## Tema

Avaliar modelos de linguagem de grande porte na deteccao de phishing em emails, combinando classificacao binaria (`phishing` vs. `safe`) com red flags explicaveis. O trabalho busca discutir desempenho e erros sob um protocolo reprodutivel, com foco em pesquisa aplicada em ciberseguranca.

## Objetivo

Comparar LLMs recentes em uma amostra controlada de emails, medindo:

- capacidade de detectar emails de phishing;
- risco de falsos negativos;
- risco de falsos positivos;
- equilibrio entre precision, recall, specificity e F1-score;
- padroes de red flags ativadas pelos modelos.

## Pergunta de Pesquisa

Em um protocolo controlado de avaliacao, quais LLMs apresentam melhor equilibrio entre deteccao de phishing, preservacao de emails legitimos e explicabilidade por red flags?

## Protocolo Experimental

O protocolo principal usa 100 emails:

- 10 emails de calibracao tecnica;
- 90 emails de avaliacao comparativa.

A calibracao valida prompt, parser, logs e lista de red flags. Ela nao entra nas metricas principais. A comparacao do artigo deve usar os 90 emails de avaliacao.

Run principal:

```text
results/comparacao_100_seed_v1/
```

Os modelos so devem entrar nas tabelas e figuras finais quando tiverem 90 respostas com `status=success`. Se um modelo estiver incompleto, mencionar como limitacao operacional ou aguardar a conclusao da rodada.

## Modelos

Modelos configurados via Groq:

- `groq-gpt-oss-120b` (`openai/gpt-oss-120b`)
- `groq-llama-3-3-70b` (`llama-3.3-70b-versatile`)
- `groq-qwen3-32b` (`qwen/qwen3-32b`)
- `groq-compound` (`groq/compound`)

O `groq/compound` pode usar modelos internos e sofrer limites de cota que afetam a conclusao da rodada. Para comparacao justa, ele nao deve ser misturado parcialmente aos demais.

## Metricas

Classe positiva: `phishing`.

- `accuracy`: proporcao geral de acertos;
- `precision`: confiabilidade dos alertas de phishing;
- `recall`: proporcao de phishing detectado;
- `specificity`: proporcao de emails seguros preservados como seguros;
- `f1`: equilibrio entre precision e recall;
- `false_positive_rate`: emails seguros marcados como phishing;
- `false_negative_rate`: phishing marcado como seguro.

Na discussao de seguranca, falsos negativos merecem destaque porque representam ataques que passariam sem alerta.

## Red Flags

As red flags sao sinais explicaveis associados a phishing, por exemplo:

- remetente suspeito;
- senso de urgencia ou medo;
- solicitacao de dados sensiveis;
- links suspeitos;
- erros gramaticais;
- email nao solicitado;
- saudacao generica;
- anexos suspeitos;
- formatacao estranha;
- oferta boa demais;
- dominio suspeito;
- historias elaboradas;
- personalizacao excessiva;
- contato ausente ou inconsistente;
- conteudo emocional;
- endereco de resposta diferente;
- botoes enganosos.

A analise deve tratar as red flags como explicacoes estruturadas geradas pelo modelo, nao como prova do raciocinio interno do LLM.

## Figuras Esperadas

Usar preferencialmente os PNGs em:

```text
results/comparacao_100_seed_v1/plots_paper/
```

Figuras planejadas:

- ranking por F1-score;
- heatmap de metricas;
- precision versus recall;
- perfil de erros;
- matrizes de confusao;
- top red flags;
- frequencia de red flags por modelo.

## Narrativa Recomendada

1. Apresentar o problema de phishing e a oportunidade de usar LLMs como classificadores explicaveis.
2. Explicar o protocolo reprodutivel: mesma amostra, mesmo prompt, mesmas red flags e mesmas metricas.
3. Separar claramente calibracao e avaliacao.
4. Comparar os modelos com base nos 90 emails avaliativos.
5. Discutir o melhor equilibrio entre recall e precision, sem olhar apenas accuracy.
6. Destacar falsos negativos como risco mais critico.
7. Usar red flags para interpretar padroes de decisao e erros.
8. Tratar falhas de API/cota como limitacao operacional relevante para reprodutibilidade.

## Limites e Cuidados

- Nao misturar resultados de calibracao com avaliacao.
- Nao comparar modelos com numeros diferentes de emails validos no resultado principal.
- Nao usar rodadas maiores como resultado central sem corte justo entre modelos.
- Nao afirmar causalidade a partir de red flags.
- Nao generalizar para todos os provedores, idiomas ou dominios de email.
- Nao ocultar falhas de API, parser ou rate limit.

## Material Exploratorio

Rodadas maiores podem ser citadas como trabalho futuro ou analise secundaria apenas se houver criterio justo. Exemplo: comparar dois modelos no mesmo corte de N emails, quando ambos tiverem pelo menos N respostas validas.

Para a versao atual do artigo, a recomendacao e manter a narrativa principal no protocolo de 100 emails, com 90 emails avaliativos.
