# Notas de Metodologia

## Pergunta de pesquisa

Como modelos LLM recentes se comparam a resultados historicos de referencia na deteccao de phishing em emails, sob um protocolo padronizado e reprodutivel?

## Protocolo experimental

1. Preparar o dataset `Phishing_Email.csv`.
2. Remover textos vazios.
3. Normalizar labels para `phishing` e `safe`.
4. Separar 10 emails de calibracao tecnica e 90 emails de avaliacao.
5. Aplicar o mesmo prompt a todos os modelos na avaliacao.
6. Exigir saida JSON com classificacao, probabilidade, red flags, scores e explicacao curta.
7. Preservar respostas brutas e CSVs individuais por modelo.
8. Calcular accuracy, precision, recall, specificity e F1-score apenas sobre os 90 emails avaliativos.
9. Gerar graficos academicos e tabelas a partir do consolidado reconstruido.
10. Discutir resultados sem misturar calibracao e avaliacao.

## Observacao sobre fake news

Os artigos de fake news sao usados apenas como base tecnica para desenho de pipeline, vetorizacao, Random Forest, SHAP e relatorios. O dominio, as features e a interpretacao cientifica permanecem em phishing.
