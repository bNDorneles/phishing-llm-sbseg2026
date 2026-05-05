from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ROOT
from src.explain import run_shap_analysis
from src.metrics import compute_metrics
from src.plots import generate_plots
from src.reports import write_reports


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenera metricas, graficos, SHAP e relatorios a partir de uma execucao existente."
    )
    parser.add_argument("--run-id", required=True, help="Nome da pasta dentro de results/.")
    parser.add_argument("--skip-shap", action="store_true", help="Nao regenera SHAP.")
    args = parser.parse_args()

    run_dir = ROOT / "results" / args.run_id
    results_path = run_dir / "final_results.csv"
    if not results_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {results_path}")

    results = pd.read_csv(results_path)
    metrics = compute_metrics(results, run_dir)
    generate_plots(results, metrics, run_dir)
    if not args.skip_shap:
        run_shap_analysis(results, run_dir)
    write_reports(ROOT / "reports", args.run_id, results, metrics)

    print(f"Artefatos regenerados para: {args.run_id}")
    print(f"Resultados: {run_dir}")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
