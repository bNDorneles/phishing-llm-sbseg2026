from __future__ import annotations

import argparse
from math import comb
from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera IC bootstrap e testes de McNemar pareados.")
    parser.add_argument("--run-dir", default="results/comparacao_100_seed_v1")
    parser.add_argument("--bootstrap-iterations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    run_dir = PROJECT_ROOT / args.run_dir
    llm = pd.read_csv(run_dir / "final_results.csv")
    llm = llm[llm["status"] == "success"][["model", "sample_id", "true_label", "predicted_label"]].copy()

    frames = [llm]
    baseline_path = run_dir / "classic_baselines_predictions.csv"
    if baseline_path.exists():
        frames.append(pd.read_csv(baseline_path)[["model", "sample_id", "true_label", "predicted_label"]])
    predictions = pd.concat(frames, ignore_index=True)

    ci = _bootstrap_ci(predictions, iterations=args.bootstrap_iterations, seed=args.seed)
    ci.to_csv(run_dir / "bootstrap_confidence_intervals.csv", index=False)

    tests = _mcnemar_tests(predictions)
    tests.to_csv(run_dir / "mcnemar_tests.csv", index=False)

    print("Bootstrap CIs:")
    print(ci.to_string(index=False))
    print("\nMcNemar:")
    print(tests.to_string(index=False))


def _bootstrap_ci(predictions: pd.DataFrame, iterations: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for model, group in predictions.groupby("model"):
        group = group.reset_index(drop=True)
        n = len(group)
        f1_values = []
        recall_values = []
        for _ in range(iterations):
            sample = group.iloc[rng.integers(0, n, n)]
            f1_values.append(_f1(sample["true_label"], sample["predicted_label"]))
            recall_values.append(_recall(sample["true_label"], sample["predicted_label"]))
        rows.append(
            {
                "model": model,
                "support": n,
                "f1_mean_bootstrap": float(np.mean(f1_values)),
                "f1_ci95_low": float(np.quantile(f1_values, 0.025)),
                "f1_ci95_high": float(np.quantile(f1_values, 0.975)),
                "recall_mean_bootstrap": float(np.mean(recall_values)),
                "recall_ci95_low": float(np.quantile(recall_values, 0.025)),
                "recall_ci95_high": float(np.quantile(recall_values, 0.975)),
            }
        )
    return pd.DataFrame(rows).sort_values("f1_mean_bootstrap", ascending=False)


def _mcnemar_tests(predictions: pd.DataFrame) -> pd.DataFrame:
    pivot_true = predictions.pivot_table(index="sample_id", columns="model", values="true_label", aggfunc="first")
    pivot_pred = predictions.pivot_table(index="sample_id", columns="model", values="predicted_label", aggfunc="first")
    models = list(pivot_pred.columns)
    rows = []
    for i, model_a in enumerate(models):
        for model_b in models[i + 1 :]:
            common = pivot_pred[[model_a, model_b]].dropna().index
            y_true = pivot_true.loc[common, model_a]
            a_correct = pivot_pred.loc[common, model_a] == y_true
            b_correct = pivot_pred.loc[common, model_b] == y_true
            b = int((a_correct & ~b_correct).sum())
            c = int((~a_correct & b_correct).sum())
            rows.append(
                {
                    "model_a": model_a,
                    "model_b": model_b,
                    "paired_samples": int(len(common)),
                    "a_correct_b_wrong": b,
                    "a_wrong_b_correct": c,
                    "mcnemar_exact_p": _exact_mcnemar_pvalue(b, c),
                }
            )
    return pd.DataFrame(rows).sort_values("mcnemar_exact_p")


def _f1(y_true: pd.Series, y_pred: pd.Series) -> float:
    tp = int(((y_true == "phishing") & (y_pred == "phishing")).sum())
    fp = int(((y_true == "safe") & (y_pred == "phishing")).sum())
    fn = int(((y_true == "phishing") & (y_pred == "safe")).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return 2 * precision * recall / max(precision + recall, 1e-12)


def _recall(y_true: pd.Series, y_pred: pd.Series) -> float:
    tp = int(((y_true == "phishing") & (y_pred == "phishing")).sum())
    fn = int(((y_true == "phishing") & (y_pred == "safe")).sum())
    return tp / max(tp + fn, 1)


def _exact_mcnemar_pvalue(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cdf = sum(comb(n, i) * (0.5**n) for i in range(k + 1))
    return min(1.0, 2 * cdf)


if __name__ == "__main__":
    main()
