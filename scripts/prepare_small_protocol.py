from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ROOT, load_experiment_config
from src.dataset import load_and_clean_dataset, stratified_sample


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepara protocolo reduzido com calibracao de red flags e avaliacao estratificada."
    )
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--total-size", type=int, default=100)
    parser.add_argument("--calibration-size", type=int, default=10)
    parser.add_argument("--safe-ratio", type=float, default=0.60)
    args = parser.parse_args()

    if args.calibration_size >= args.total_size:
        raise ValueError("--calibration-size deve ser menor que --total-size")

    config = load_experiment_config()
    if not config.input_dataset.exists():
        raise FileNotFoundError(
            f"Dataset bruto nao encontrado: {config.input_dataset}. Rode scripts/prepare_dataset.py primeiro."
        )

    total_safe = round(args.total_size * args.safe_ratio)
    total_phishing = args.total_size - total_safe
    calibration_safe = round(args.calibration_size * args.safe_ratio)
    calibration_phishing = args.calibration_size - calibration_safe
    eval_size = args.total_size - args.calibration_size
    eval_safe = total_safe - calibration_safe
    eval_phishing = total_phishing - calibration_phishing

    df = load_and_clean_dataset(config.input_dataset)
    calibration = stratified_sample(
        df,
        sample_size=args.calibration_size,
        seed=args.seed,
        target_safe=calibration_safe,
        target_phishing=calibration_phishing,
    )
    remaining = df[~df["sample_id"].isin(calibration["sample_id"])].copy()
    evaluation = stratified_sample(
        remaining,
        sample_size=eval_size,
        seed=args.seed + 1,
        target_safe=eval_safe,
        target_phishing=eval_phishing,
    )

    calibration = calibration.copy()
    evaluation = evaluation.copy()
    calibration["protocol_split"] = "calibration"
    evaluation["protocol_split"] = "evaluation"
    protocol = pd.concat(
        [
            calibration[["sample_id", "email_text", "true_label", "protocol_split"]],
            evaluation[["sample_id", "email_text", "true_label", "protocol_split"]],
        ],
        ignore_index=True,
    )

    output_dir = ROOT / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    protocol_path = output_dir / f"phishing_protocol_{args.total_size}_seed{args.seed}.csv"
    calibration_path = output_dir / f"phishing_calibration_{args.calibration_size}_seed{args.seed}.csv"
    evaluation_path = output_dir / f"phishing_eval_{eval_size}_seed{args.seed}.csv"

    protocol.to_csv(protocol_path, index=False)
    calibration[["sample_id", "email_text", "true_label"]].to_csv(calibration_path, index=False)
    evaluation[["sample_id", "email_text", "true_label"]].to_csv(evaluation_path, index=False)

    print(f"Protocolo salvo em: {protocol_path}")
    print(f"Calibracao salva em: {calibration_path}")
    print(f"Avaliacao salva em: {evaluation_path}")
    print("\nDistribuicao total:")
    print(protocol["true_label"].value_counts().to_string())
    print("\nCalibracao:")
    print(calibration["true_label"].value_counts().to_string())
    print("\nAvaliacao:")
    print(evaluation["true_label"].value_counts().to_string())


if __name__ == "__main__":
    main()
