from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ROOT, load_experiment_config, load_model_configs
from src.dataset import prepare_sample
from src.explain import run_shap_analysis
from src.metrics import compute_metrics
from src.pipeline import run_model_on_dataset
from src.plots import generate_plots
from src.reports import update_changelog, write_reports
from src.utils import setup_logging, timestamp


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa avaliacao comparativa de LLMs para phishing.")
    parser.add_argument("--models", nargs="*", help="Nomes dos modelos a executar. Padrao: enabled em config/models.yaml.")
    parser.add_argument("--limit", type=int, help="Limita quantidade de emails para teste rapido.")
    parser.add_argument("--run-id", help="Identificador manual da execucao.")
    args = parser.parse_args()

    experiment = load_experiment_config()
    run_id = args.run_id or timestamp()
    run_dir = ROOT / "results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(run_dir / "experiment.log")
    logging.info("Iniciando run %s", run_id)

    if experiment.sample_dataset.exists():
        dataset = pd.read_csv(experiment.sample_dataset)
    else:
        dataset = prepare_sample(
            input_path=experiment.input_dataset,
            output_path=experiment.sample_dataset,
            sample_size=experiment.sample_size,
            seed=experiment.seed,
            target_safe=experiment.target_safe,
            target_phishing=experiment.target_phishing,
        )

    models = load_model_configs(only_enabled=True)
    if args.models:
        requested = set(args.models)
        all_models = load_model_configs(only_enabled=False)
        models = [model for model in all_models if model.name in requested]
        missing = requested.difference({model.name for model in models})
        if missing:
            raise ValueError(f"Modelos nao encontrados em config/models.yaml: {sorted(missing)}")
    if not models:
        raise ValueError("Nenhum modelo habilitado ou selecionado.")

    all_results = []
    for model in models:
        model_results = run_model_on_dataset(dataset, model, experiment, run_dir, limit=args.limit)
        model_results.to_csv(run_dir / f"results_{model.name}.csv", index=False)
        all_results.append(model_results)

    results = pd.concat(all_results, ignore_index=True)
    results.to_csv(run_dir / "final_results.csv", index=False)
    errors = results[results["parse_error"].fillna("") != ""]
    errors.to_csv(run_dir / "parse_errors.csv", index=False)
    false_positives = results[(results["true_label"] == "safe") & (results["predicted_label"] == "phishing")]
    false_negatives = results[(results["true_label"] == "phishing") & (results["predicted_label"] == "safe")]
    false_positives.to_csv(run_dir / "false_positives.csv", index=False)
    false_negatives.to_csv(run_dir / "false_negatives.csv", index=False)

    metrics = compute_metrics(results, run_dir)
    generate_plots(results, metrics, run_dir)
    run_shap_analysis(results, run_dir)
    update_changelog(ROOT / "reports", run_id, [model.name for model in models], len(results))
    write_reports(ROOT / "reports", run_id, results, metrics)

    print(f"Run concluida: {run_id}")
    print(f"Resultados: {run_dir}")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
