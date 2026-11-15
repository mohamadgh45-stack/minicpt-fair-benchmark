"""Extract the Excel workbooks embedded in the MSc thesis (.docx) into data/raw/.

Why this script exists
----------------------
A .docx file is really a ZIP archive. Every chart in the Word file keeps its
numbers in a small Excel workbook stored under ``word/embeddings/``. Those
workbooks are the only surviving copy of the raw test data.

This script copies them out *unchanged* and writes a manifest with a SHA-256
checksum for each file. A checksum is a fingerprint: if even one byte of a
file changes later, its checksum changes too. Anyone can re-run the script
and verify that the raw data in this repository is exactly what was in the
thesis.

Usage
-----
    python src/extract_raw.py path/to/thesis.docx
"""

import argparse
import csv
import hashlib
import re
import zipfile
from pathlib import Path

EMBEDDINGS_FOLDER = "word/embeddings/"


def natural_key(name: str) -> int:
    """Sort 'Worksheet2' before 'Worksheet10' (plain sorting would not)."""
    numbers = re.findall(r"\d+", name)
    return int(numbers[-1]) if numbers else 0


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("thesis_docx", type=Path, help="path to the thesis .docx file")
    parser.add_argument("--out", type=Path, default=Path("data/raw/thesis_embedded"),
                        help="folder for the extracted workbooks")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    manifest_rows = []

    with zipfile.ZipFile(args.thesis_docx) as docx:
        workbook_names = [n for n in docx.namelist()
                          if n.startswith(EMBEDDINGS_FOLDER) and n.endswith(".xlsx")]
        for name in sorted(workbook_names, key=natural_key):
            data = docx.read(name)
            target = args.out / Path(name).name
            target.write_bytes(data)
            manifest_rows.append({
                "file": target.name,
                "bytes": len(data),
                "sha256": sha256_of(data),
                "source": f"thesis .docx, {name}",
            })

    manifest_path = args.out / "MANIFEST.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "bytes", "sha256", "source"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Extracted {len(manifest_rows)} workbooks to {args.out}")
    print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
