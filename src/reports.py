from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.red_flags import RED_FLAGS


def update_changelog(reports_dir: Path, run_id: str, models: list[str], sample_size: int) -> None:
    path = reports_dir / "CHANGELOG_EXPERIMENTOS.md"
    entry = (
        f"\n## {run_id}\n"
        f"- Data/hora: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Modelos: {', '.join(models)}\n"
        f"- Tamanho da amostra: {sample_size}\n"
        f"- Artefatos: `results/{run_id}`\n"
    )
    if not path.exists():
        path.write_text("# Changelog de Experimentos\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def write_reports(reports_dir: Path, run_id: str, results: pd.DataFrame, metrics: pd.DataFrame) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_executive_summary(reports_dir / "06_resumo_executivo.md", run_id, results, metrics)
    _write_metrics(reports_dir / "07_metricas_resultados.md", run_id, metrics)
    _write_red_flags(reports_dir / "08_analise_red_flags.md", run_id, results)
    _write_shap(reports_dir / "09_analise_shap.md", run_id)
    _write_errors(reports_dir / "10_analise_erros.md", run_id, results)
    _write_limitations(reports_dir / "11_limitacoes.md")


def _write_metrics(path: Path, run_id: str, metrics: pd.DataFrame) -> None:
    ordered = metrics.sort_values(["f1", "recall", "precision"], ascending=False)
    display_columns = [
        "model",
        "input_count",
        "support",
        "failed_count",
        "coverage_rate",
        "accuracy",
        "precision",
        "recall",
        "specificity",
        "f1",
        "false_positive_rate",
        "false_negative_rate",
        "tp",
        "tn",
        "fp",
        "fn",
    ]
    path.write_text(
        f"# 07 - Metricas e Resultados\n\nRun: `{run_id}`\n\n"
        + _table(_format_metric_percentages(ordered[display_columns]))
        + "\n\n"
        "As metricas usam `phishing` como classe positiva.\n\n"
        "- `precision`: entre os alertas de phishing, quantos eram phishing de fato.\n"
        "- `recall`: entre os phishing reais, quantos foram detectados.\n"
        "- `specificity`: entre os e-mails safe reais, quantos foram preservados como safe.\n"
        "- `false_negative_rate`: phishing que passou como safe; e o erro mais critico em seguranca.\n"
        "- `false_positive_rate`: e-mail safe classificado como phishing.\n",
        encoding="utf-8",
    )


def _write_red_flags(path: Path, run_id: str, results: pd.DataFrame) -> None:
    freq = results.groupby("model")[RED_FLAGS].mean().reset_index()
    top_flags = (
        results[RED_FLAGS]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .rename_axis("red_flag")
        .reset_index(name="frequencia_media")
    )
    path.write_text(
        f"# 08 - Analise de Red Flags\n\nRun: `{run_id}`\n\n"
        "## Top 10 red flags mais ativadas\n\n"
        + _table(_format_metric_percentages(top_flags))
        + "\n\n## Frequencia por modelo\n\n"
        + _table(_format_metric_percentages(freq))
        + "\n\nValores representam frequencia media de ativacao por modelo.\n",
        encoding="utf-8",
    )


def _write_shap(path: Path, run_id: str) -> None:
    path.write_text(
        f"# 09 - Analise SHAP\n\nRun: `{run_id}`\n\n"
        "Artefatos esperados:\n"
        f"- `results/{run_id}/shap/shap_summary.png`\n"
        f"- `results/{run_id}/shap/shap_importance.csv`\n\n"
        "A analise usa Random Forest sobre as red flags extraidas para estimar importancia das features.\n",
        encoding="utf-8",
    )


def _write_errors(path: Path, run_id: str, results: pd.DataFrame) -> None:
    fp = results[(results["true_label"] == "safe") & (results["predicted_label"] == "phishing")]
    fn = results[(results["true_label"] == "phishing") & (results["predicted_label"] == "safe")]
    rows = []
    for model, group in results.groupby("model"):
        model_fp = int(((group["true_label"] == "safe") & (group["predicted_label"] == "phishing")).sum())
        model_fn = int(((group["true_label"] == "phishing") & (group["predicted_label"] == "safe")).sum())
        safe_total = int((group["true_label"] == "safe").sum())
        phishing_total = int((group["true_label"] == "phishing").sum())
        rows.append(
            {
                "model": model,
                "false_positives": model_fp,
                "false_negatives": model_fn,
                "false_positive_rate": model_fp / max(safe_total, 1),
                "false_negative_rate": model_fn / max(phishing_total, 1),
            }
        )
    errors_by_model = pd.DataFrame(rows).sort_values(["false_negatives", "false_positives", "model"])
    body = (
        f"# 10 - Analise de Erros\n\nRun: `{run_id}`\n\n"
        f"- Falsos positivos: {len(fp)}\n"
        f"- Falsos negativos: {len(fn)}\n\n"
        "## Erros por modelo\n\n"
        + _table(_format_metric_percentages(errors_by_model))
        + "\n\n"
        "Arquivos CSV detalhados ficam no diretorio de resultados da execucao.\n"
    )
    path.write_text(body, encoding="utf-8")


def _write_limitations(path: Path) -> None:
    path.write_text(
        "# 11 - Limitacoes\n\n"
        "- Dataset em ingles; resultados nao generalizam diretamente para emails em portugues.\n"
        "- Saidas de LLMs podem variar entre datas, versoes e modelos disponibilizados pela Groq.\n"
        "- O baseline historico deve ser comparado separadamente, sem mistura com novas inferencias.\n"
        "- SHAP explica o classificador Random Forest treinado sobre red flags, nao o raciocinio interno dos LLMs.\n"
        "- Custos e limites de API podem restringir repeticoes experimentais com todos os modelos.\n",
        encoding="utf-8",
    )


def _table(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return "```text\n" + df.to_string(index=False) + "\n```"


def _write_executive_summary(path: Path, run_id: str, results: pd.DataFrame, metrics: pd.DataFrame) -> None:
    ordered = metrics.sort_values(["f1", "recall", "precision"], ascending=False).reset_index(drop=True)
    best = ordered.iloc[0]
    phishing_total = int((results["true_label"] == "phishing").sum() / max(results["model"].nunique(), 1))
    safe_total = int((results["true_label"] == "safe").sum() / max(results["model"].nunique(), 1))
    body = (
        f"# 06 - Resumo Executivo\n\nRun: `{run_id}`\n\n"
        f"- Amostra por modelo: {phishing_total + safe_total} e-mails "
        f"({safe_total} safe, {phishing_total} phishing).\n"
        f"- Melhor modelo por F1-score: `{best['model']}`.\n"
        f"- Cobertura do melhor modelo: {best['coverage_rate']:.1%}.\n"
        f"- F1 do melhor modelo: {best['f1']:.1%}.\n"
        f"- Recall do melhor modelo: {best['recall']:.1%}.\n"
        f"- Precision do melhor modelo: {best['precision']:.1%}.\n"
        f"- Falsos negativos do melhor modelo: {int(best['fn'])}.\n\n"
        "## Leaderboard\n\n"
        + _table(
            _format_metric_percentages(
                ordered[["model", "coverage_rate", "accuracy", "precision", "recall", "specificity", "f1", "fp", "fn"]]
            )
        )
        + "\n\n"
        "Leitura recomendada: para deteccao de phishing, `recall` e `false_negative_rate` merecem atencao especial, "
        "pois falsos negativos representam ataques que passaram como e-mails seguros.\n"
    )
    path.write_text(body, encoding="utf-8")


def _format_metric_percentages(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()
    percent_columns = [
        column
        for column in formatted.columns
        if column
        in {
            "accuracy",
            "balanced_accuracy",
            "coverage_rate",
            "precision",
            "recall",
            "specificity",
            "f1",
            "false_positive_rate",
            "false_negative_rate",
            "frequencia_media",
        }
        or column in RED_FLAGS
    ]
    for column in percent_columns:
        formatted[column] = formatted[column].map(lambda value: f"{float(value):.1%}")
    return formatted
