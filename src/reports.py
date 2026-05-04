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
    _write_metrics(reports_dir / "07_metricas_resultados.md", run_id, metrics)
    _write_red_flags(reports_dir / "08_analise_red_flags.md", run_id, results)
    _write_shap(reports_dir / "09_analise_shap.md", run_id)
    _write_errors(reports_dir / "10_analise_erros.md", run_id, results)
    _write_limitations(reports_dir / "11_limitacoes.md")


def _write_metrics(path: Path, run_id: str, metrics: pd.DataFrame) -> None:
    path.write_text(
        f"# 07 - Metricas e Resultados\n\nRun: `{run_id}`\n\n"
        + _table(metrics)
        + "\n\nAs metricas usam `phishing` como classe positiva.\n",
        encoding="utf-8",
    )


def _write_red_flags(path: Path, run_id: str, results: pd.DataFrame) -> None:
    freq = results.groupby("model")[RED_FLAGS].mean().reset_index()
    path.write_text(
        f"# 08 - Analise de Red Flags\n\nRun: `{run_id}`\n\n"
        + _table(freq)
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
    body = (
        f"# 10 - Analise de Erros\n\nRun: `{run_id}`\n\n"
        f"- Falsos positivos: {len(fp)}\n"
        f"- Falsos negativos: {len(fn)}\n\n"
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
