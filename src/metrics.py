from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
except ModuleNotFoundError:
    accuracy_score = confusion_matrix = f1_score = precision_score = recall_score = None


def compute_metrics(results: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    rows = []
    for model, group in results.groupby("model"):
        y_true = group["true_label"]
        y_pred = group["predicted_label"]
        tp = int(((y_true == "phishing") & (y_pred == "phishing")).sum())
        tn = int(((y_true == "safe") & (y_pred == "safe")).sum())
        fp = int(((y_true == "safe") & (y_pred == "phishing")).sum())
        fn = int(((y_true == "phishing") & (y_pred == "safe")).sum())
        total = max(len(group), 1)
        accuracy = (tp + tn) / total
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        rows.append(
            {
                "model": model,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "tp": tp,
                "tn": tn,
                "fp": fp,
                "fn": fn,
            }
        )
    metrics = pd.DataFrame(rows).sort_values("f1", ascending=False)
    metrics.to_csv(output_dir / "metrics_by_model.csv", index=False)
    return metrics
