from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import replace
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
    parser.add_argument("--resume", action="store_true", help="Reaproveita sucessos existentes no mesmo run-id e processa apenas pendentes/falhas.")
    parser.add_argument("--dataset", help="CSV de amostra ja preparada. Ex.: data/processed/phishing_eval_90_seed2026.csv.")
    parser.add_argument("--max-email-chars", type=int, help="Sobrescreve o corte maximo de caracteres por email nesta execucao.")
    args = parser.parse_args()

    experiment = load_experiment_config()
    if args.max_email_chars:
        experiment = replace(experiment, max_email_chars=args.max_email_chars)
    run_id = args.run_id or timestamp()
    run_dir = ROOT / "results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(run_dir / "experiment.log")
    logging.info("Iniciando run %s", run_id)

    if args.dataset:
        dataset_path = _resolve_project_path(args.dataset)
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset informado nao encontrado: {dataset_path}")
        dataset = pd.read_csv(dataset_path)
    elif experiment.sample_dataset.exists():
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

    requested_models = args.models or _models_from_env()
    models = load_model_configs(only_enabled=True)
    if requested_models:
        requested = set(requested_models)
        all_models = load_model_configs(only_enabled=False)
        models = [model for model in all_models if model.name in requested]
        missing = requested.difference({model.name for model in models})
        if missing:
            raise ValueError(f"Modelos nao encontrados em config/models.yaml: {sorted(missing)}")
    if not models:
        raise ValueError("Nenhum modelo habilitado ou selecionado.")

    all_results = []
    target_dataset = dataset.head(args.limit).copy() if args.limit else dataset.copy()
    for model in models:
        model_results = _run_or_resume_model(
            target_dataset=target_dataset,
            model=model,
            experiment=experiment,
            run_dir=run_dir,
            resume=args.resume,
        )
        all_results.append(model_results)

    results = pd.concat(all_results, ignore_index=True)
    _validate_global_coverage(results)
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


def _models_from_env() -> list[str]:
    value = os.environ.get("GROQ_MODELS", "").strip()
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _run_or_resume_model(
    *,
    target_dataset: pd.DataFrame,
    model,
    experiment,
    run_dir: Path,
    resume: bool,
) -> pd.DataFrame:
    result_path = run_dir / f"results_{model.name}.csv"
    if not resume or not result_path.exists():
        model_results = run_model_on_dataset(
            target_dataset,
            model,
            experiment,
            run_dir,
            limit=None,
            checkpoint_path=result_path,
        )
        model_results.to_csv(result_path, index=False)
        return model_results

    existing = pd.read_csv(result_path)
    target_ids = set(target_dataset["sample_id"].astype(str))
    existing = existing[existing["sample_id"].astype(str).isin(target_ids)].copy()
    successful_existing = existing[existing["status"] == "success"].copy()
    successful_ids = set(successful_existing["sample_id"].astype(str))
    pending_dataset = target_dataset[~target_dataset["sample_id"].astype(str).isin(successful_ids)].copy()

    logging.info(
        "Retomando %s: total=%s, sucessos_existentes=%s, pendentes=%s",
        model.name,
        len(target_dataset),
        len(successful_existing),
        len(pending_dataset),
    )

    if pending_dataset.empty:
        combined = successful_existing
    else:
        new_results = run_model_on_dataset(
            pending_dataset,
            model,
            experiment,
            run_dir,
            limit=None,
            checkpoint_path=result_path,
            checkpoint_existing=successful_existing,
        )
        combined = pd.concat([successful_existing, new_results], ignore_index=True)

    combined = combined.drop_duplicates(subset=["sample_id", "model"], keep="last")
    combined = combined.sort_values("sample_id").reset_index(drop=True)
    combined.to_csv(result_path, index=False)
    _write_resume_batch_summary(combined, run_dir, model, len(target_dataset))
    return combined


def _write_resume_batch_summary(results: pd.DataFrame, run_dir: Path, model, expected_total: int) -> None:
    success_count = int((results["status"] == "success").sum()) if "status" in results.columns else 0
    failed_count = int((results["status"] == "failed").sum()) if "status" in results.columns else 0
    processed_total = success_count + failed_count
    summary = {
        "model": model.name,
        "model_id": model.model_id,
        "provider": model.provider,
        "total_entrada": expected_total,
        "total_processado_sucesso": success_count,
        "total_processado_falha": failed_count,
        "total_contabilizado": processed_total,
        "coverage_ok": expected_total == processed_total,
        "resume_summary": True,
    }
    (run_dir / f"batch_summary_{model.name}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _validate_global_coverage(results: pd.DataFrame) -> None:
    if "status" not in results.columns:
        return
    by_model = results.groupby("model")["status"].value_counts().unstack(fill_value=0)
    by_model["total_contabilizado"] = by_model.sum(axis=1)
    for model, row in by_model.iterrows():
        success = int(row.get("success", 0))
        failed = int(row.get("failed", 0))
        total = int(row["total_contabilizado"])
        if total != success + failed:
            raise RuntimeError(f"Cobertura invalida para {model}: total={total}, success={success}, failed={failed}")


if __name__ == "__main__":
    main()
