from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa resultados historicos para pasta separada.")
    parser.add_argument(
        "--zip-path",
        default=None,
        help="Caminho para o ZIP com resultados historicos.",
    )
    args = parser.parse_args()
    if not args.zip_path:
        raise ValueError("Informe --zip-path caminho/para/resultados_historicos.zip")
    zip_path = Path(args.zip_path)
    output_dir = ROOT / "data" / "baseline_historico"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP nao encontrado: {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.namelist():
            if member.lower().endswith((".csv", ".md", ".json", ".txt")):
                archive.extract(member, output_dir)
    print(f"Baseline historico importado em {output_dir}")
    print("Observacao: esses arquivos nao sao misturados automaticamente aos novos resultados.")


if __name__ == "__main__":
    main()
