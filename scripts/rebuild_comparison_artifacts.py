from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ROOT
from src.metrics import compute_metrics
from src.plots import generate_plots
from src.reports import write_reports


DEFAULT_MODELS = [
    "groq-gpt-oss-120b",
    "groq-llama-3-3-70b",
    "groq-qwen3-32b",
    "groq-compound",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstrui final_results.csv, metricas, relatorios e plots academicos "
            "a partir dos CSVs individuais de uma rodada comparativa."
        )
    )
    parser.add_argument("--run-id", default="comparacao_100_seed_v1", help="Pasta dentro de results/.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Modelos esperados na comparacao, na ordem desejada.",
    )
    parser.add_argument(
        "--min-success",
        type=int,
        default=90,
        help="Minimo de respostas com status=success para incluir um modelo no comparativo final.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Inclui modelos incompletos. Nao recomendado para as figuras principais do artigo.",
    )
    parser.add_argument(
        "--paper-plots-dir",
        default="plots_paper",
        help="Subpasta onde os PNGs academicos serao gerados.",
    )
    args = parser.parse_args()

    run_dir = ROOT / "results" / args.run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"Pasta de resultados nao encontrada: {run_dir}")

    selected_frames: list[pd.DataFrame] = []
    status_rows = []
    for model in args.models:
        path = run_dir / f"results_{model}.csv"
        if not path.exists():
            status_rows.append(_status_row(model, path, "missing", 0, 0, 0, False))
            continue

        df = pd.read_csv(path)
        if "status" not in df.columns:
            df["status"] = "success"
        success_count = int((df["status"] == "success").sum())
        failed_count = int((df["status"] == "failed").sum())
        include = bool(args.allow_partial or success_count >= args.min_success)
        status_rows.append(_status_row(model, path, "found", len(df), success_count, failed_count, include))
        if include:
            selected_frames.append(df)

    if not selected_frames:
        raise RuntimeError(
            "Nenhum modelo atingiu o criterio de inclusao. "
            "Use --allow-partial apenas para diagnostico, nao para o paper."
        )

    final_results = pd.concat(selected_frames, ignore_index=True)
    final_results = final_results.sort_values(["model", "sample_id"], kind="stable")
    final_results.to_csv(run_dir / "final_results.csv", index=False)
    _write_error_slices(final_results, run_dir)

    metrics = compute_metrics(final_results, run_dir)
    generate_plots(final_results, metrics, run_dir, plots_subdir=args.paper_plots_dir, paper_style=True)
    write_reports(ROOT / "reports", args.run_id, final_results, metrics)
    _write_manifest(run_dir, args, status_rows, metrics)

    print(f"Reconstrucao concluida: {run_dir}")
    print(f"Modelos incluidos: {', '.join(metrics['model'].tolist())}")
    skipped = [row["model"] for row in status_rows if not row["included"]]
    if skipped:
        print(f"Modelos fora do comparativo final: {', '.join(skipped)}")
    print(metrics.to_string(index=False))


def _status_row(
    model: str,
    path: Path,
    file_status: str,
    rows: int,
    success_count: int,
    failed_count: int,
    included: bool,
) -> dict[str, object]:
    return {
        "model": model,
        "path": str(path),
        "file_status": file_status,
        "rows": rows,
        "success_count": success_count,
        "failed_count": failed_count,
        "included": included,
    }


def _write_error_slices(results: pd.DataFrame, run_dir: Path) -> None:
    success = results[results["status"] == "success"].copy() if "status" in results.columns else results.copy()
    false_positives = success[(success["true_label"] == "safe") & (success["predicted_label"] == "phishing")]
    false_negatives = success[(success["true_label"] == "phishing") & (success["predicted_label"] == "safe")]
    parse_errors = results[results["status"] != "success"].copy() if "status" in results.columns else results.iloc[0:0]

    false_positives.to_csv(run_dir / "false_positives.csv", index=False)
    false_negatives.to_csv(run_dir / "false_negatives.csv", index=False)
    parse_errors.to_csv(run_dir / "parse_errors.csv", index=False)


def _write_manifest(run_dir: Path, args: argparse.Namespace, status_rows: list[dict[str, object]], metrics: pd.DataFrame) -> None:
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": args.run_id,
        "min_success": args.min_success,
        "allow_partial": args.allow_partial,
        "paper_plots_dir": args.paper_plots_dir,
        "model_inputs": status_rows,
        "included_models": metrics["model"].tolist(),
        "note": (
            "Comparativo principal usa apenas modelos com pelo menos min_success respostas validas. "
            "Modelos incompletos permanecem preservados nos CSVs individuais."
        ),
    }
    (run_dir / "rebuild_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
