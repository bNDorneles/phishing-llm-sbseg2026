from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.red_flags import RED_FLAGS


def generate_plots(results: pd.DataFrame, metrics: pd.DataFrame, output_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ModuleNotFoundError:
        (output_dir / "plots_skipped.txt").write_text(
            "Graficos nao gerados: instale matplotlib e seaborn.\n",
            encoding="utf-8",
        )
        return

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    plt.figure(figsize=(8, 4))
    sns.barplot(data=metrics, x="model", y="f1", color="#2f7d6d")
    plt.ylim(0, 1)
    plt.title("Comparacao de F1-score por modelo")
    plt.tight_layout()
    plt.savefig(plots_dir / "comparacao_f1.png", dpi=180)
    plt.close()

    melted = metrics.melt(id_vars="model", value_vars=["accuracy", "precision", "recall", "f1"])
    plt.figure(figsize=(10, 5))
    sns.barplot(data=melted, x="model", y="value", hue="variable")
    plt.ylim(0, 1)
    plt.title("Metricas por modelo")
    plt.tight_layout()
    plt.savefig(plots_dir / "metricas_por_modelo.png", dpi=180)
    plt.close()

    flag_frequency = results.groupby("model")[RED_FLAGS].mean().reset_index()
    flag_frequency.to_csv(output_dir / "red_flag_frequency.csv", index=False)
    plt.figure(figsize=(12, 6))
    sns.heatmap(flag_frequency.set_index("model"), cmap="YlGnBu", vmin=0, vmax=1)
    plt.title("Frequencia media de red flags por modelo")
    plt.tight_layout()
    plt.savefig(plots_dir / "frequencia_red_flags.png", dpi=180)
    plt.close()

    for model, group in results.groupby("model"):
        tp = int(((group["true_label"] == "phishing") & (group["predicted_label"] == "phishing")).sum())
        fn = int(((group["true_label"] == "phishing") & (group["predicted_label"] == "safe")).sum())
        fp = int(((group["true_label"] == "safe") & (group["predicted_label"] == "phishing")).sum())
        tn = int(((group["true_label"] == "safe") & (group["predicted_label"] == "safe")).sum())
        cm = [[tp, fn], [fp, tn]]
        plt.figure(figsize=(4, 3.5))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=["phishing", "safe"], yticklabels=["phishing", "safe"])
        plt.xlabel("Predito")
        plt.ylabel("Real")
        plt.title(f"Matriz de confusao - {model}")
        plt.tight_layout()
        plt.savefig(plots_dir / f"matriz_confusao_{model}.png", dpi=180)
        plt.close()
