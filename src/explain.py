from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.red_flags import RED_FLAGS


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
    values = shap_values[1] if isinstance(shap_values, list) else shap_values
    importance = pd.DataFrame(
        {"feature": RED_FLAGS, "importance": abs(values).mean(axis=0)}
    ).sort_values("importance", ascending=False)
    importance.to_csv(shap_dir / "shap_importance.csv", index=False)

    plt.figure(figsize=(10, 6))
    shap.summary_plot(values, x_test, show=False, plot_size=(10, 6))
    plt.tight_layout()
    plt.savefig(shap_dir / "shap_summary.png", dpi=180, bbox_inches="tight")
    plt.close()
