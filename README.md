# minicpt-fair-benchmark

Re-engineering the data of my MSc mini-CPT campaign (Amirkabir University of
Technology, 2019) into a documented, reproducible dataset — and using the
lessons learned to design metadata and quality-control rules for GPR utility
surveys.

**Status:** work in progress.

## Repository structure

| Folder | Contents |
| --- | --- |
| `data/raw/` | Original data, never edited. Each file is listed with its SHA-256 checksum in `MANIFEST.csv`. |
| `data/processed/` | Data produced by the scripts in `src/`. Can always be regenerated. |
| `src/` | Python scripts, run in the order below. |
| `metadata/` | Metadata schema and one record per test (coming next). |
| `reports/` | Quality-control reports (coming next). |
| `docs/` | Measurement protocol and data management plan (coming next). |

## How to reproduce

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python src/extract_raw.py path/to/thesis.docx   # only needed once
python src/build_tidy.py
```

## Data

18 mini-CPT tests on sand–kaolinite mixtures (10, 30 and 50 % clay) with 0, 4
and 8 % crude oil, penetrated at 20 mm/s to 80 cm, one reading per 2 cm.
Test codes read `clay.moisture.oil[.extra water]`, all in percent.
