from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ROOT, load_experiment_config
from src.dataset import prepare_sample


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara o dataset Phishing_Email.csv e a amostra estratificada.")
    parser.add_argument(
        "--zip-path",
        default=None,
        help="Caminho opcional para Phishing_Email.csv.zip. Se omitido, procura em data/raw/.",
    )
    args = parser.parse_args()
    config = load_experiment_config()
    raw_dir = ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if not config.input_dataset.exists():
        zip_path = Path(args.zip_path) if args.zip_path else raw_dir / "Phishing_Email.csv.zip"
        if not zip_path.exists():
            raise FileNotFoundError(
                "Dataset nao encontrado. Coloque Phishing_Email.csv em data/raw/ "
                "ou informe --zip-path caminho/para/Phishing_Email.csv.zip."
            )
        with zipfile.ZipFile(zip_path) as archive:
            csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not csv_members:
                raise FileNotFoundError("Nenhum CSV encontrado dentro do ZIP.")
            member = csv_members[0]
            with archive.open(member) as source, config.input_dataset.open("wb") as target:
                target.write(source.read())
        print(f"CSV extraido para {config.input_dataset}")
    else:
        print(f"CSV ja existe em {config.input_dataset}")

    sample = prepare_sample(
        input_path=config.input_dataset,
        output_path=config.sample_dataset,
        sample_size=config.sample_size,
        seed=config.seed,
        target_safe=config.target_safe,
        target_phishing=config.target_phishing,
    )
    print(f"Amostra salva em {config.sample_dataset}")
    print(sample["true_label"].value_counts().to_string())


if __name__ == "__main__":
    main()
