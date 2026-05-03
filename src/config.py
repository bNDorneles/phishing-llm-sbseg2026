from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    seed: int
    sample_size: int
    target_safe: int
    target_phishing: int
    input_dataset: Path
    sample_dataset: Path
    max_email_chars: int
    retry_attempts: int
    retry_sleep_seconds: int


@dataclass(frozen=True)
class ModelConfig:
    name: str
    provider: str
    enabled: bool
    model_id: str
    temperature: float
    max_tokens: int


def read_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml

        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except ModuleNotFoundError:
        return _read_minimal_yaml(path)


def _read_minimal_yaml(path: Path) -> dict[str, Any]:
    """Parser pequeno para os YAMLs simples deste projeto quando PyYAML nao estiver instalado."""
    with path.open("r", encoding="utf-8") as handle:
        lines = [line.rstrip() for line in handle if line.strip() and not line.lstrip().startswith("#")]
    if path.name == "experiment.yaml":
        data: dict[str, Any] = {}
        for line in lines[1:]:
            key, value = line.strip().split(":", 1)
            data[key] = _coerce_scalar(value.strip())
        return {"experiment": data}
    if path.name == "models.yaml":
        models: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("- "):
                if current:
                    models.append(current)
                current = {}
                key, value = stripped[2:].split(":", 1)
                current[key] = _coerce_scalar(value.strip())
            elif current is not None and ":" in stripped:
                key, value = stripped.split(":", 1)
                current[key] = _coerce_scalar(value.strip())
        if current:
            models.append(current)
        return {"models": models}
    raise ModuleNotFoundError("PyYAML nao instalado e parser minimo so cobre config do projeto.")


def _coerce_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def load_experiment_config(path: Path | None = None) -> ExperimentConfig:
    data = read_yaml(path or ROOT / "config" / "experiment.yaml")["experiment"]
    return ExperimentConfig(
        name=data["name"],
        seed=int(data["seed"]),
        sample_size=int(data["sample_size"]),
        target_safe=int(data.get("target_safe", 0)),
        target_phishing=int(data.get("target_phishing", 0)),
        input_dataset=ROOT / data["input_dataset"],
        sample_dataset=ROOT / data["sample_dataset"],
        max_email_chars=int(data["max_email_chars"]),
        retry_attempts=int(data["retry_attempts"]),
        retry_sleep_seconds=int(data["retry_sleep_seconds"]),
    )


def load_model_configs(path: Path | None = None, only_enabled: bool = True) -> list[ModelConfig]:
    rows = read_yaml(path or ROOT / "config" / "models.yaml")["models"]
    configs = [
        ModelConfig(
            name=row["name"],
            provider=row["provider"],
            enabled=bool(row.get("enabled", False)),
            model_id=row["model_id"],
            temperature=float(row.get("temperature", 0.0)),
            max_tokens=int(row.get("max_tokens", 700)),
        )
        for row in rows
    ]
    return [item for item in configs if item.enabled] if only_enabled else configs
