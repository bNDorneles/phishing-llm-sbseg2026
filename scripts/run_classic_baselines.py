from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset import load_and_clean_dataset


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Treina baselines classicas fora do protocolo e avalia nos mesmos 90 emails dos LLMs."
    )
    parser.add_argument("--raw-dataset", default="data/raw/Phishing_Email.csv")
    parser.add_argument("--protocol-dataset", default="data/processed/phishing_protocol_100_seed2026.csv")
    parser.add_argument("--eval-dataset", default="data/processed/phishing_eval_90_seed2026.csv")
    parser.add_argument("--output-dir", default="results/comparacao_100_seed_v1")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
        from sklearn.pipeline import Pipeline
    except ModuleNotFoundError as exc:
        raise SystemExit(f"Dependencia ausente para baselines classicas: {exc}") from exc

    raw = load_and_clean_dataset(PROJECT_ROOT / args.raw_dataset)
    protocol = pd.read_csv(PROJECT_ROOT / args.protocol_dataset)
    eval_df = pd.read_csv(PROJECT_ROOT / args.eval_dataset)

    held_out_ids = set(protocol["sample_id"].astype(str))
    train_df = raw[~raw["sample_id"].isin(held_out_ids)].copy()
    eval_df = eval_df.merge(raw[["sample_id", "email_text", "true_label"]], on="sample_id", suffixes=("", "_raw"))
    eval_df["email_text"] = eval_df["email_text"].fillna(eval_df["email_text_raw"])
    eval_df["true_label"] = eval_df["true_label"].fillna(eval_df["true_label_raw"])

    baselines = {
        "tfidf_logistic_regression": Pipeline(
            steps=[
                ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_features=50000)),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        random_state=args.seed,
                    ),
                ),
            ]
        ),
        "tfidf_random_forest": Pipeline(
            steps=[
                ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_features=30000)),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=300,
                        class_weight="balanced",
                        random_state=args.seed,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }

    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    prediction_frames = []
    y_test = eval_df["true_label"].astype(str)
    for name, model in baselines.items():
        model.fit(train_df["email_text"].astype(str), train_df["true_label"].astype(str))
        y_pred = pd.Series(model.predict(eval_df["email_text"].astype(str)), index=eval_df.index)

        tp = int(((y_test == "phishing") & (y_pred == "phishing")).sum())
        tn = int(((y_test == "safe") & (y_pred == "safe")).sum())
        fp = int(((y_test == "safe") & (y_pred == "phishing")).sum())
        fn = int(((y_test == "phishing") & (y_pred == "safe")).sum())
        recall = recall_score(y_test, y_pred, pos_label="phishing", zero_division=0)
        specificity = tn / max(tn + fp, 1)
        rows.append(
            {
                "model": name,
                "type": "classical_baseline",
                "train_count": int(len(train_df)),
                "support": int(len(eval_df)),
                "phishing_support": int((y_test == "phishing").sum()),
                "safe_support": int((y_test == "safe").sum()),
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred, pos_label="phishing", zero_division=0),
                "recall": recall,
                "specificity": specificity,
                "f1": f1_score(y_test, y_pred, pos_label="phishing", zero_division=0),
                "false_positive_rate": fp / max(fp + tn, 1),
                "false_negative_rate": fn / max(fn + tp, 1),
                "tp": tp,
                "tn": tn,
                "fp": fp,
                "fn": fn,
            }
        )
        prediction_frames.append(
            pd.DataFrame(
                {
                    "model": name,
                    "sample_id": eval_df["sample_id"],
                    "true_label": y_test,
                    "predicted_label": y_pred,
                    "status": "success",
                }
            )
        )

    metrics = pd.DataFrame(rows).sort_values("f1", ascending=False)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    metrics.to_csv(output_dir / "classic_baselines_metrics.csv", index=False)
    predictions.to_csv(output_dir / "classic_baselines_predictions.csv", index=False)
    _write_combined_metrics(output_dir, metrics)
    print(metrics.to_string(index=False))


def _write_combined_metrics(output_dir: Path, baseline_metrics: pd.DataFrame) -> None:
    llm_metrics_path = output_dir / "metrics_by_model.csv"
    if not llm_metrics_path.exists():
        return
    llm = pd.read_csv(llm_metrics_path).copy()
    llm["type"] = "LLM"
    llm["train_count"] = ""
    baseline = baseline_metrics.copy()
    baseline["type"] = "classical_baseline"
    common = [
        "model",
        "type",
        "train_count",
        "support",
        "accuracy",
        "precision",
        "recall",
        "specificity",
        "f1",
        "fp",
        "fn",
    ]
    combined = pd.concat([llm.reindex(columns=common), baseline.reindex(columns=common)], ignore_index=True)
    combined.sort_values(["f1", "recall", "precision"], ascending=False).to_csv(
        output_dir / "model_comparison_with_classic_baselines.csv", index=False
    )


if __name__ == "__main__":
    main()
