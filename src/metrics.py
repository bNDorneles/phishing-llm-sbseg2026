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
        eval_group = group[group["status"] == "success"].copy() if "status" in group.columns else group.copy()
        failed_count = int((group["status"] == "failed").sum()) if "status" in group.columns else 0
        y_true = eval_group["true_label"]
        y_pred = eval_group["predicted_label"]
        tp = int(((y_true == "phishing") & (y_pred == "phishing")).sum())
        tn = int(((y_true == "safe") & (y_pred == "safe")).sum())
        fp = int(((y_true == "safe") & (y_pred == "phishing")).sum())
        fn = int(((y_true == "phishing") & (y_pred == "safe")).sum())
        total = max(len(eval_group), 1)
        input_count = int(len(group))
        phishing_support = int((y_true == "phishing").sum())
        safe_support = int((y_true == "safe").sum())
        accuracy = (tp + tn) / total
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        specificity = tn / max(tn + fp, 1)
        false_positive_rate = fp / max(fp + tn, 1)
        false_negative_rate = fn / max(fn + tp, 1)
        balanced_accuracy = (recall + specificity) / 2
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        rows.append(
            {
                "model": model,
                "input_count": input_count,
                "support": int(total),
                "failed_count": failed_count,
                "coverage_rate": (len(eval_group) + failed_count) / max(input_count, 1),
                "phishing_support": phishing_support,
                "safe_support": safe_support,
                "accuracy": accuracy,
                "balanced_accuracy": balanced_accuracy,
                "precision": precision,
                "recall": recall,
                "specificity": specificity,
                "f1": f1,
                "false_positive_rate": false_positive_rate,
                "false_negative_rate": false_negative_rate,
                "tp": tp,
                "tn": tn,
                "fp": fp,
                "fn": fn,
            }
        )
    metrics = pd.DataFrame(rows).sort_values("f1", ascending=False)
    metrics.to_csv(output_dir / "metrics_by_model.csv", index=False)
    return metrics
