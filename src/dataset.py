from __future__ import annotations

from pathlib import Path

import pandas as pd


LABEL_MAP = {
    "phishing email": "phishing",
    "phishing": "phishing",
    "safe email": "safe",
    "safe": "safe",
}


def load_and_clean_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"Email Text", "Email Type"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Dataset sem colunas obrigatorias: {sorted(missing)}")

    cleaned = df.rename(columns={"Email Text": "email_text", "Email Type": "true_label"}).copy()
    cleaned["email_text"] = cleaned["email_text"].fillna("").astype(str).str.strip()
    cleaned = cleaned[cleaned["email_text"] != ""]
    cleaned["true_label"] = (
        cleaned["true_label"].fillna("").astype(str).str.strip().str.lower().map(LABEL_MAP)
    )
    cleaned = cleaned.dropna(subset=["true_label"]).reset_index(drop=True)
    cleaned.insert(0, "sample_id", [f"email_{idx:05d}" for idx in range(len(cleaned))])
    return cleaned[["sample_id", "email_text", "true_label"]]


def stratified_sample(
    df: pd.DataFrame,
    sample_size: int,
    seed: int,
    target_safe: int = 0,
    target_phishing: int = 0,
) -> pd.DataFrame:
    if target_safe and target_phishing:
        safe_n = target_safe
        phishing_n = target_phishing
        if safe_n + phishing_n != sample_size:
            raise ValueError("target_safe + target_phishing deve ser igual a sample_size")
    else:
        counts = df["true_label"].value_counts(normalize=True)
        phishing_n = round(sample_size * counts.get("phishing", 0.0))
        safe_n = sample_size - phishing_n
    parts = []
    for label, n in [("phishing", phishing_n), ("safe", safe_n)]:
        label_df = df[df["true_label"] == label]
        if len(label_df) < n:
            raise ValueError(f"Amostra pedida para {label} ({n}) maior que disponivel ({len(label_df)})")
        parts.append(label_df.sample(n=n, random_state=seed))
    return pd.concat(parts).sample(frac=1.0, random_state=seed).reset_index(drop=True)


def prepare_sample(
    input_path: Path,
    output_path: Path,
    sample_size: int,
    seed: int,
    target_safe: int = 0,
    target_phishing: int = 0,
) -> pd.DataFrame:
    df = load_and_clean_dataset(input_path)
    sample = stratified_sample(
        df,
        sample_size=sample_size,
        seed=seed,
        target_safe=target_safe,
        target_phishing=target_phishing,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(output_path, index=False)
    return sample
