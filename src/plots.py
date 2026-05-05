from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.red_flags import RED_FLAGS


DISPLAY_METRICS = ["accuracy", "precision", "recall", "specificity", "f1"]


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
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.titleweight": "bold",
            "axes.labelcolor": "#253238",
            "xtick.color": "#253238",
            "ytick.color": "#253238",
        }
    )

    metrics = metrics.copy().sort_values(["f1", "recall", "precision"], ascending=False)
    _plot_leaderboard(metrics, plots_dir, plt, sns)
    _plot_metrics_heatmap(metrics, plots_dir, plt, sns)
    _plot_precision_recall(metrics, plots_dir, plt, sns)
    _plot_error_profile(metrics, plots_dir, plt, sns)
    _plot_confusion_matrices(results, plots_dir, plt, sns)
    _plot_red_flags(results, output_dir, plots_dir, plt, sns)


def _plot_leaderboard(metrics: pd.DataFrame, plots_dir: Path, plt, sns) -> None:
    plt.figure(figsize=(11, max(4, 0.7 * len(metrics))))
    ax = sns.barplot(data=metrics, y="model", x="f1", color="#2f7d6d")
    ax.set_xlim(0, 1)
    ax.set_xlabel("F1-score para classe phishing")
    ax.set_ylabel("")
    ax.set_title("Ranking dos modelos por F1-score")
    for container in ax.containers:
        ax.bar_label(container, fmt="%.2f", padding=4)
    _add_caption(
        ax,
        "F1 combina precision e recall. Para phishing, ele resume o equilibrio entre detectar ataques e evitar alarmes falsos.",
    )
    plt.tight_layout()
    plt.savefig(plots_dir / "01_ranking_f1.png", dpi=200, bbox_inches="tight")
    plt.close()


def _plot_metrics_heatmap(metrics: pd.DataFrame, plots_dir: Path, plt, sns) -> None:
    heatmap = metrics.set_index("model")[DISPLAY_METRICS].sort_values("f1", ascending=False)
    annotations = heatmap.apply(lambda column: column.map(lambda value: f"{value:.0%}"))
    plt.figure(figsize=(10, max(3.5, 0.55 * len(heatmap))))
    ax = sns.heatmap(
        heatmap,
        annot=annotations,
        fmt="",
        cmap="YlGnBu",
        vmin=0,
        vmax=1,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Valor da metrica"},
    )
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Painel comparativo de metricas")
    ax.set_xticklabels(["Accuracy", "Precision", "Recall", "Specificity", "F1"], rotation=0)
    _add_caption(
        ax,
        "Recall mede phishing capturado. Specificity mede e-mails safe preservados. Precision mede confiabilidade dos alertas.",
    )
    plt.tight_layout()
    plt.savefig(plots_dir / "02_metricas_heatmap.png", dpi=200, bbox_inches="tight")
    plt.close()


def _plot_precision_recall(metrics: pd.DataFrame, plots_dir: Path, plt, sns) -> None:
    plt.figure(figsize=(8, 6))
    ax = sns.scatterplot(
        data=metrics,
        x="precision",
        y="recall",
        size="f1",
        hue="f1",
        sizes=(120, 420),
        palette="viridis",
        legend=False,
    )
    for _, row in metrics.iterrows():
        ax.annotate(row["model"], (row["precision"], row["recall"]), xytext=(7, 5), textcoords="offset points")
    ax.set_xlim(0, 1.04)
    ax.set_ylim(0, 1.04)
    ax.set_xlabel("Precision: alertas de phishing corretos")
    ax.set_ylabel("Recall: phishing detectado")
    ax.set_title("Trade-off entre precision e recall")
    _add_caption(
        ax,
        "O canto superior direito e o melhor: detecta mais phishing e erra menos ao acusar e-mails seguros.",
    )
    plt.tight_layout()
    plt.savefig(plots_dir / "03_precision_recall.png", dpi=200, bbox_inches="tight")
    plt.close()


def _plot_error_profile(metrics: pd.DataFrame, plots_dir: Path, plt, sns) -> None:
    errors = metrics[["model", "fp", "fn"]].melt(id_vars="model", var_name="tipo", value_name="quantidade")
    errors["tipo"] = errors["tipo"].map({"fp": "Falso positivo\nsafe -> phishing", "fn": "Falso negativo\nphishing -> safe"})
    plt.figure(figsize=(11, max(4, 0.65 * metrics["model"].nunique())))
    ax = sns.barplot(data=errors, y="model", x="quantidade", hue="tipo", palette=["#d7902f", "#b8463f"])
    ax.set_xlabel("Quantidade de erros")
    ax.set_ylabel("")
    ax.set_title("Perfil de erros por modelo")
    for container in ax.containers:
        ax.bar_label(container, fmt="%.0f", padding=3)
    _add_caption(
        ax,
        "Falso negativo e mais critico em seguranca: phishing passou como safe. Falso positivo gera alarme indevido.",
    )
    plt.tight_layout()
    plt.savefig(plots_dir / "04_erros_fp_fn.png", dpi=200, bbox_inches="tight")
    plt.close()


def _plot_confusion_matrices(results: pd.DataFrame, plots_dir: Path, plt, sns) -> None:
    for model, group in results.groupby("model"):
        tp = int(((group["true_label"] == "phishing") & (group["predicted_label"] == "phishing")).sum())
        fn = int(((group["true_label"] == "phishing") & (group["predicted_label"] == "safe")).sum())
        fp = int(((group["true_label"] == "safe") & (group["predicted_label"] == "phishing")).sum())
        tn = int(((group["true_label"] == "safe") & (group["predicted_label"] == "safe")).sum())
        cm = pd.DataFrame(
            [[tp, fn], [fp, tn]],
            index=["Real phishing", "Real safe"],
            columns=["Predito phishing", "Predito safe"],
        )
        phishing_total = max(tp + fn, 1)
        safe_total = max(fp + tn, 1)
        annotations = pd.DataFrame(
            [
                [f"{tp}\n{tp / phishing_total:.0%} dos phishing", f"{fn}\n{fn / phishing_total:.0%} dos phishing"],
                [f"{fp}\n{fp / safe_total:.0%} dos safe", f"{tn}\n{tn / safe_total:.0%} dos safe"],
            ],
            index=cm.index,
            columns=cm.columns,
        )
        plt.figure(figsize=(6.3, 5))
        ax = sns.heatmap(cm, annot=annotations, fmt="", cmap="Blues", cbar=False, linewidths=0.5, linecolor="white")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title(f"Matriz de confusao interpretada\n{model}")
        _add_caption(ax, "Linhas mostram a classe real. Colunas mostram a decisao do modelo.")
        plt.tight_layout()
        plt.savefig(plots_dir / f"05_matriz_confusao_{model}.png", dpi=200, bbox_inches="tight")
        plt.close()


def _plot_red_flags(results: pd.DataFrame, output_dir: Path, plots_dir: Path, plt, sns) -> None:
    flag_frequency = results.groupby("model")[RED_FLAGS].mean().reset_index()
    flag_frequency.to_csv(output_dir / "red_flag_frequency.csv", index=False)

    overall = (
        results[RED_FLAGS]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .rename_axis("red_flag")
        .reset_index(name="frequency")
    )
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(data=overall, y="red_flag", x="frequency", color="#4d77a8")
    ax.set_xlim(0, max(0.05, min(1, overall["frequency"].max() * 1.15)))
    ax.set_xlabel("Frequencia media de ativacao")
    ax.set_ylabel("")
    ax.set_title("Top 10 red flags mais ativadas")
    for container in ax.containers:
        ax.bar_label(container, labels=[f"{value:.0%}" for value in overall["frequency"]], padding=4)
    _add_caption(ax, "Mostra quais sinais aparecem com mais frequencia nas respostas dos modelos.")
    plt.tight_layout()
    plt.savefig(plots_dir / "06_top_red_flags.png", dpi=200, bbox_inches="tight")
    plt.close()

    heatmap = flag_frequency.set_index("model")
    plt.figure(figsize=(14, max(4, 0.55 * len(heatmap))))
    ax = sns.heatmap(heatmap, cmap="YlGnBu", vmin=0, vmax=1, linewidths=0.35, linecolor="white")
    ax.set_xlabel("Red flags")
    ax.set_ylabel("")
    ax.set_title("Frequencia de red flags por modelo")
    plt.xticks(rotation=45, ha="right")
    _add_caption(ax, "Valores maiores indicam que o modelo marcou aquela red flag com mais frequencia.")
    plt.tight_layout()
    plt.savefig(plots_dir / "07_red_flags_por_modelo.png", dpi=200, bbox_inches="tight")
    plt.close()


def _add_caption(ax, text: str) -> None:
    ax.text(0, -0.18, text, transform=ax.transAxes, ha="left", va="top", fontsize=9, color="#52616b")
