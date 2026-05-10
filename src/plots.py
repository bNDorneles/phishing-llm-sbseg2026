from __future__ import annotations

from pathlib import Path
from textwrap import wrap

import pandas as pd

from src.red_flags import RED_FLAGS


DISPLAY_METRICS = ["accuracy", "precision", "recall", "specificity", "f1"]
MODEL_LABELS = {
    "groq-gpt-oss-120b": "GPT-OSS 120B",
    "groq-llama-3-3-70b": "Llama 3.3 70B",
    "groq-qwen3-32b": "Qwen3 32B",
    "groq-compound": "Compound",
}
METRIC_LABELS = {
    "accuracy": "Accuracy",
    "precision": "Precision",
    "recall": "Recall",
    "specificity": "Specificity",
    "f1": "F1-score",
}
MODEL_PALETTE = {
    "groq-qwen3-32b": "#1f6f8b",
    "groq-llama-3-3-70b": "#2f7d6d",
    "groq-gpt-oss-120b": "#8a6f2a",
    "groq-compound": "#b65f3b",
}

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


def generate_plots(
    results: pd.DataFrame,
    metrics: pd.DataFrame,
    output_dir: Path,
    plots_subdir: str = "plots",
    paper_style: bool = False,
) -> None:
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ModuleNotFoundError:
        (output_dir / "plots_skipped.txt").write_text(
            "Graficos nao gerados: instale matplotlib e seaborn.\n",
            encoding="utf-8",
        )
        return

    plots_dir = output_dir / plots_subdir
    plots_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="paper" if paper_style else "notebook")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.titleweight": "bold",
            "axes.titlesize": 12 if paper_style else 13,
            "axes.labelsize": 10,
            "axes.labelcolor": "#253238",
            "axes.edgecolor": "#9aa6ac",
            "grid.color": "#d9e0e3",
            "grid.linewidth": 0.7,
            "xtick.color": "#253238",
            "ytick.color": "#253238",
            "legend.frameon": False,
            "savefig.dpi": 300 if paper_style else 200,
        }
    )

    metrics = metrics.copy().sort_values(["f1", "recall", "precision"], ascending=False)
    metrics["model_label"] = metrics["model"].map(MODEL_LABELS).fillna(metrics["model"])
    _plot_leaderboard(metrics, plots_dir, plt, sns, paper_style)
    _plot_metrics_heatmap(metrics, plots_dir, plt, sns, paper_style)
    _plot_precision_recall(metrics, plots_dir, plt, sns, paper_style)
    _plot_error_profile(metrics, plots_dir, plt, sns, paper_style)
    _plot_confusion_matrices(results, plots_dir, plt, sns, paper_style)
    _plot_red_flags(results, output_dir, plots_dir, plt, sns, paper_style)


def _plot_leaderboard(metrics: pd.DataFrame, plots_dir: Path, plt, sns, paper_style: bool) -> None:
    ordered = metrics.sort_values("f1", ascending=True)
    colors = [MODEL_PALETTE.get(model, "#4f6f7a") for model in ordered["model"]]
    plt.figure(figsize=(7.4, max(2.7, 0.52 * len(metrics))) if paper_style else (9.5, max(3.6, 0.62 * len(metrics))))
    ax = sns.barplot(data=ordered, y="model_label", x="f1", palette=colors, hue="model_label", legend=False)
    ax.set_xlim(0, 1)
    ax.set_xlabel("F1-score")
    ax.set_ylabel("")
    ax.set_title("Comparacao por F1-score")
    for index, (_, row) in enumerate(ordered.iterrows()):
        ax.text(
            min(row["f1"] + 0.012, 0.965),
            index,
            f"{row['f1']:.1%}",
            va="center",
            fontsize=8.0 if paper_style else 8.5,
            color="#253238",
        )
    if not paper_style:
        _add_caption(
            ax,
            "F1-score calculado sobre respostas validas. O n indica o suporte avaliado; falhas de API aparecem separadamente.",
        )
    plt.tight_layout()
    plt.savefig(plots_dir / "01_ranking_f1.png", bbox_inches="tight")
    plt.close()


def _plot_metrics_heatmap(metrics: pd.DataFrame, plots_dir: Path, plt, sns, paper_style: bool) -> None:
    heatmap = metrics.set_index("model_label")[DISPLAY_METRICS].sort_values("f1", ascending=False)
    annotations = heatmap.apply(lambda column: column.map(lambda value: f"{value:.0%}"))
    plt.figure(figsize=(7.4, max(2.5, 0.45 * len(heatmap))) if paper_style else (9.5, max(3.4, 0.5 * len(heatmap))))
    ax = sns.heatmap(
        heatmap,
        annot=annotations,
        fmt="",
        cmap="YlGnBu",
        vmin=0,
        vmax=1,
        linewidths=0.8,
        linecolor="white",
        annot_kws={"fontsize": 8.2 if paper_style else 9},
        cbar_kws={"label": "Valor", "shrink": 0.82},
    )
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Metricas de classificacao")
    ax.set_xticklabels([METRIC_LABELS[column] for column in DISPLAY_METRICS], rotation=0)
    if not paper_style:
        _add_caption(
            ax,
            "Recall mede phishing detectado; specificity mede e-mails legitimos preservados; precision mede confiabilidade dos alertas.",
        )
    plt.tight_layout()
    plt.savefig(plots_dir / "02_metricas_heatmap.png", bbox_inches="tight")
    plt.close()


def _plot_precision_recall(metrics: pd.DataFrame, plots_dir: Path, plt, sns, paper_style: bool) -> None:
    plt.figure(figsize=(5.8, 4.4) if paper_style else (7.2, 5.4))
    ax = sns.scatterplot(
        data=metrics,
        x="precision",
        y="recall",
        size="f1",
        hue="model",
        sizes=(140, 420),
        palette=MODEL_PALETTE,
        legend=False,
    )
    offsets = [(7, 7), (7, -12), (-70, 7), (-70, -12), (7, 18)]
    for index, (_, row) in enumerate(metrics.iterrows()):
        ax.annotate(
            row["model_label"],
            (row["precision"], row["recall"]),
            xytext=offsets[index % len(offsets)],
            textcoords="offset points",
            fontsize=8.2 if paper_style else 9,
        )
    ax.set_xlim(0, 1.04)
    ax.set_ylim(0, 1.04)
    ax.axhline(0.9, color="#c5cdd1", linewidth=0.8, linestyle="--")
    ax.axvline(0.9, color="#c5cdd1", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Precision")
    ax.set_ylabel("Recall")
    ax.set_title("Precision versus recall")
    if not paper_style:
        _add_caption(
            ax,
            "O canto superior direito indica melhor equilibrio: mais phishing detectado e menos alertas falsos.",
        )
    plt.tight_layout()
    plt.savefig(plots_dir / "03_precision_recall.png", bbox_inches="tight")
    plt.close()


def _plot_error_profile(metrics: pd.DataFrame, plots_dir: Path, plt, sns, paper_style: bool) -> None:
    error_columns = ["fp", "fn"]
    if int(metrics["failed_count"].sum()) > 0:
        error_columns.append("failed_count")

    errors = metrics[["model_label", *error_columns]].melt(
        id_vars="model_label", var_name="tipo", value_name="quantidade"
    )
    errors["tipo"] = errors["tipo"].map(
        {
            "fp": "Falso positivo",
            "fn": "Falso negativo",
            "failed_count": "Falha API/parser",
        }
    )
    hue_order = [
        "Falso positivo",
        "Falso negativo",
    ]
    palette = ["#c9913f", "#b45757"]
    if "failed_count" in error_columns:
        hue_order.append("Falha API/parser")
        palette.append("#6b7280")
    plt.figure(
        figsize=(8.2, max(3.0, 0.56 * metrics["model"].nunique()))
        if paper_style
        else (10.2, max(3.9, 0.66 * metrics["model"].nunique()))
    )
    ax = sns.barplot(
        data=errors,
        y="model_label",
        x="quantidade",
        hue="tipo",
        hue_order=hue_order,
        palette=palette,
    )
    ax.set_xlabel("Quantidade de erros")
    ax.set_ylabel("")
    ax.set_title("Erros por modelo", pad=10)
    max_error = max(1, int(errors["quantidade"].max()))
    ax.set_xlim(0, max_error + 1.0)
    for container in ax.containers:
        labels = [f"{bar.get_width():.0f}" if bar.get_width() > 0 else "" for bar in container]
        ax.bar_label(container, labels=labels, padding=3, fontsize=8 if paper_style else 9)
    ax.legend(
        title="",
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        ncol=1,
        frameon=False,
        handlelength=1.4,
        fontsize=8.2 if paper_style else 9,
    )
    plt.tight_layout()
    plt.savefig(plots_dir / "04_erros_fp_fn.png", bbox_inches="tight")
    plt.close()


def _plot_confusion_matrices(results: pd.DataFrame, plots_dir: Path, plt, sns, paper_style: bool) -> None:
    for model, group in results.groupby("model"):
        if "status" in group.columns:
            group = group[group["status"] == "success"]
        tp = int(((group["true_label"] == "phishing") & (group["predicted_label"] == "phishing")).sum())
        fn = int(((group["true_label"] == "phishing") & (group["predicted_label"] == "safe")).sum())
        fp = int(((group["true_label"] == "safe") & (group["predicted_label"] == "phishing")).sum())
        tn = int(((group["true_label"] == "safe") & (group["predicted_label"] == "safe")).sum())
        cm = pd.DataFrame(
            [[tp, fn], [fp, tn]],
            index=["Real: phishing", "Real: legitimo"],
            columns=["Predito: phishing", "Predito: legitimo"],
        )
        phishing_total = max(tp + fn, 1)
        safe_total = max(fp + tn, 1)
        annotations = pd.DataFrame(
            [
                [f"VP\n{tp} ({tp / phishing_total:.0%})", f"FN\n{fn} ({fn / phishing_total:.0%})"],
                [f"FP\n{fp} ({fp / safe_total:.0%})", f"VN\n{tn} ({tn / safe_total:.0%})"],
            ],
            index=cm.index,
            columns=cm.columns,
        )
        plt.figure(figsize=(5.8, 5.2) if paper_style else (6.3, 5.4))
        ax = sns.heatmap(
            cm,
            annot=annotations,
            fmt="",
            cmap="YlGnBu",
            cbar=False,
            linewidths=0.8,
            linecolor="white",
            square=True,
            annot_kws={"fontsize": 10 if paper_style else 11},
        )
        ax.set_xlabel("")
        ax.set_ylabel("")
        title = MODEL_LABELS.get(model, model)
        ax.set_title(f"Matriz de confusao: {title}")
        ax.tick_params(axis="x", labelrotation=0)
        ax.tick_params(axis="y", labelrotation=0)
        ax.set_yticklabels(ax.get_yticklabels(), ha="right", va="center")
        _add_caption(
            ax,
            "VP: phishing detectado | FN: phishing perdido | FP: alerta falso | VN: email legitimo preservado",
            y=-0.18 if paper_style else -0.14,
        )
        plt.tight_layout()
        plt.savefig(plots_dir / f"05_matriz_confusao_{model}.png", bbox_inches="tight")
        plt.close()


def _plot_red_flags(results: pd.DataFrame, output_dir: Path, plots_dir: Path, plt, sns, paper_style: bool) -> None:
    success_results = results[results["status"] == "success"].copy() if "status" in results.columns else results.copy()
    flag_frequency = success_results.groupby("model")[RED_FLAGS].mean().reset_index()
    flag_frequency.to_csv(output_dir / "red_flag_frequency.csv", index=False)
    flag_frequency["model_label"] = flag_frequency["model"].map(MODEL_LABELS).fillna(flag_frequency["model"])

    overall = (
        success_results[RED_FLAGS]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .rename_axis("red_flag")
        .reset_index(name="frequency")
    )
    overall["red_flag_label"] = overall["red_flag"].map(_format_red_flag_label)
    plt.figure(figsize=(7.4, 4.8) if paper_style else (9.5, 5.8))
    ax = sns.barplot(data=overall, y="red_flag_label", x="frequency", color="#3d6f91")
    ax.set_xlim(0, max(0.05, min(1, overall["frequency"].max() * 1.15)))
    ax.set_xlabel("Frequencia media de ativacao")
    ax.set_ylabel("")
    ax.set_title("Red flags mais frequentes")
    for container in ax.containers:
        ax.bar_label(
            container,
            labels=[f"{value:.0%}" for value in overall["frequency"]],
            padding=4,
            fontsize=8 if paper_style else 9,
        )
    if not paper_style:
        _add_caption(ax, "Mostra quais sinais aparecem com mais frequencia nas respostas dos modelos.")
    plt.tight_layout()
    plt.savefig(plots_dir / "06_top_red_flags.png", bbox_inches="tight")
    plt.close()

    heatmap = flag_frequency.set_index("model_label")[RED_FLAGS].T
    heatmap.index = [_format_red_flag_label(flag, width=28 if paper_style else 32) for flag in RED_FLAGS]
    annotations = heatmap.apply(lambda column: column.map(lambda value: f"{value:.0%}" if value >= 0.005 else ""))
    fig, ax = plt.subplots(
        figsize=(7.6, max(6.8, 0.36 * len(heatmap))) if paper_style else (10.0, max(7.0, 0.42 * len(heatmap)))
    )
    sns.heatmap(
        heatmap,
        ax=ax,
        annot=annotations,
        fmt="",
        annot_kws={"fontsize": 6.8 if paper_style else 7.5},
        cmap="YlGnBu",
        vmin=0,
        vmax=1,
        linewidths=0.6,
        linecolor="white",
        cbar_kws={"label": "Frequencia", "shrink": 0.78},
    )
    ax.set_xlabel("Modelos")
    ax.set_ylabel("Red flags")
    ax.set_title("Frequencia de red flags por modelo")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0, ha="center")
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, ha="right", va="center")
    ax.tick_params(axis="x", labelsize=8.5 if paper_style else 9, pad=8)
    ax.tick_params(axis="y", labelsize=7.2 if paper_style else 8.5, pad=8)
    ax.set_xlabel("Modelos", labelpad=10)
    if not paper_style:
        _add_caption(ax, "Valores maiores indicam que o modelo marcou aquela red flag com mais frequencia.", y=-0.34)
    fig.subplots_adjust(left=0.33 if paper_style else 0.30, right=0.96, top=0.92, bottom=0.08)
    plt.savefig(plots_dir / "07_red_flags_por_modelo.png", bbox_inches="tight")
    plt.close()


def _format_red_flag_label(flag: str, width: int | None = None) -> str:
    label = RED_FLAG_LABELS.get(flag, flag.replace("_", " ").title())
    if width is None:
        return label
    return "\n".join(wrap(label, width=width, break_long_words=False))


def _add_caption(ax, text: str, y: float = -0.18) -> None:
    ax.text(0, y, text, transform=ax.transAxes, ha="left", va="top", fontsize=9, color="#52616b")
