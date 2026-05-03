# Notas de Metodologia

## Pergunta de pesquisa

Como modelos LLM recentes se comparam a resultados historicos de referencia na deteccao de phishing em emails, sob um protocolo padronizado e reprodutivel?

## Protocolo experimental

1. Preparar o dataset `Phishing_Email.csv`.
2. Remover textos vazios.
3. Normalizar labels para `phishing` e `safe`.
4. Selecionar amostra estratificada de 1.009 emails com seed 42.
5. Aplicar o mesmo prompt a todos os modelos.
6. Exigir saida JSON com classificacao, probabilidade, red flags, scores e explicacao curta.
7. Preservar respostas brutas.
8. Calcular accuracy, precision, recall e F1-score.
9. Treinar Random Forest sobre red flags para analise SHAP.
10. Comparar resultados novos com baseline historico, sem misturar os CSVs.

## Observacao sobre fake news

Os artigos de fake news sao usados apenas como base tecnica para desenho de pipeline, vetorizacao, Random Forest, SHAP e relatorios. O dominio, as features e a interpretacao cientifica permanecem em phishing.
