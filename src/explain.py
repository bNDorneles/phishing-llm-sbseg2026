from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.red_flags import RED_FLAGS


RED_FLAG_LABELS = {
    "remetente_suspeito": "Remetente suspeito",
    "senso_urgencia_medo": "Urgencia ou medo",
    "solicitacao_dados_sensiveis": "Dados sensiveis",
    "links_suspeitos": "Links suspeitos",
    "erros_gramaticais": "Erros gramaticais",
    "email_nao_solicitado": "Email nao solicitado",
    "saudacao_generica": "Saudacao generica",
    "anexos_suspeitos": "Anexos suspeitos",
    "formatacao_estranha": "Formatacao estranha",
    "oferta_boa_demais": "Oferta boa demais",
    "dominio_suspeito": "Dominio suspeito",
    "historias_elaboradas": "Historias elaboradas",
    "personalizacao_excessiva": "Personalizacao excessiva",
    "contato_ausente_ou_inconsistente": "Contato ausente ou inconsistente",
    "conteudo_emocional": "Conteudo emocional",
    "endereco_resposta_diferente": "Endereco de resposta diferente",
    "botoes_enganosos": "Botoes enganosos",
}


def run_shap_analysis(results: pd.DataFrame, output_dir: Path) -> None:
    shap_dir = output_dir / "shap"
    shap_dir.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib.pyplot as plt
        import shap
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
    except ModuleNotFoundError:
        (shap_dir / "shap_skipped.txt").write_text(
            "SHAP nao gerado: instale shap, scikit-learn e matplotlib.\n",
            encoding="utf-8",
        )
        return

    if results.empty or not set(RED_FLAGS).issubset(results.columns):
        return

    # Usa uma linha por email/modelo: explica como as red flags predizem o rotulo real.
    x = results[RED_FLAGS].fillna(0).astype(int)
    y = (results["true_label"] == "phishing").astype(int)
    if y.nunique() < 2 or len(x) < 10:
        return

    x_train, x_test, y_train, _ = train_test_split(x, y, test_size=0.25, random_state=42, stratify=y)
    clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
    clf.fit(x_train, y_train)

    explainer = shap.TreeExplainer(clf)
    shap_values = explainer.shap_values(x_test)
    values = _positive_class_shap_values(shap_values, n_features=len(RED_FLAGS))
    if values.ndim != 2 or values.shape[1] != len(RED_FLAGS):
        (shap_dir / "shap_skipped.txt").write_text(
            f"SHAP nao gerado: formato inesperado {values.shape} para {len(RED_FLAGS)} red flags.\n",
            encoding="utf-8",
        )
        return

    importance = pd.DataFrame(
        {"feature": RED_FLAGS, "importance": abs(values).mean(axis=0)}
    ).sort_values("importance", ascending=False)
    importance.to_csv(shap_dir / "shap_importance.csv", index=False)

    x_display = x_test.rename(columns=RED_FLAG_LABELS)
    plt.figure(figsize=(10.5, 7.2))
    shap.summary_plot(values, x_display, show=False, plot_size=(10.5, 7.2))
    fig = plt.gcf()
    ax = plt.gca()
    ax.set_title("Impacto das red flags na predicao de phishing", fontsize=13, fontweight="bold", pad=14)
    ax.set_xlabel("Valor SHAP: impacto na predicao de phishing")
    for item in fig.axes:
        if item is not ax:
            if item.get_ylabel() == "Feature value":
                item.set_ylabel("Valor da red flag")
            tick_labels = [tick.get_text() for tick in item.get_yticklabels()]
            if tick_labels == ["Low", "High"]:
                item.set_yticklabels(["Baixo", "Alto"])
    fig.text(
        0.01,
        0.01,
        "Pontos = emails avaliados. SHAP positivo aumenta a predicao de phishing; negativo reduz. "
        "Vermelho = red flag presente/forte; azul = ausente/fraca.",
        ha="left",
        va="bottom",
        fontsize=9,
        color="#374151",
    )
    plt.tight_layout(rect=(0, 0.06, 1, 0.96))
    plt.savefig(shap_dir / "shap_summary.png", dpi=300, bbox_inches="tight")
    plt.close()


def _positive_class_shap_values(shap_values: Any, n_features: int) -> np.ndarray:
    """Normaliza saidas do SHAP para matriz 2D: amostras x features.

    Dependendo da versao, classificacao binaria pode retornar lista por classe
    ou array 3D com a dimensao de classes no ultimo eixo.
    """
    if isinstance(shap_values, list):
        values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
    else:
        values = shap_values

    array = np.asarray(values)
    if array.ndim == 3:
        if array.shape[1] == n_features:
            class_index = 1 if array.shape[2] > 1 else 0
            array = array[:, :, class_index]
        elif array.shape[2] == n_features:
            class_index = 1 if array.shape[0] > 1 else 0
            array = array[class_index, :, :]
    return np.asarray(array)
