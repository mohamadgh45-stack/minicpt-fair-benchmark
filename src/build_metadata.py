"""Create one metadata record per test and check each one against the schema.

Why this script exists
----------------------
A metadata record answers two questions about a test:
  * descriptive: what was tested, under which conditions?
  * provenance:  where do the numbers come from, and how were they produced?

Information shared by all tests (materials, equipment, procedure) is stored
once, in metadata/campaign.json. Each test record stores only what is specific
to that test, and points to the campaign by its id.

Every record is validated against metadata/schema/cpt_test.schema.json. The
schema is a contract: it says which fields must exist, what type they have and
which values are allowed. A record that breaks the contract is rejected before
it can enter the dataset.

Unknown values are written as null, never left out or guessed. "We don't know
the test date" is itself information.

Usage
-----
    python src/build_metadata.py
"""

import argparse
import json
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

CAMPAIGN_ID = "AUT-MINICPT-2018"


def record_for(test_id: str, rows: pd.DataFrame) -> dict:
    first = rows.iloc[0]
    # The depth-0 row is all zeros and has no formula, so it is ignored here.
    patterns = rows.loc[rows["depth_cm"] > 0, "derived_force"].unique()
    derived = patterns[0] if len(patterns) == 1 else "none"

    notes = []
    if derived == "none":
        notes.append("All three forces were typed in by hand; total is not guaranteed to equal tip + sleeve.")

    return {
        "test_id": test_id,
        "campaign_id": CAMPAIGN_ID,
        "condition": {
            "clay_pct": int(first["clay_pct"]),
            "target_moisture_pct": float(first["moisture_pct"]),
            "moisture_basis": "gravimetric",
            "oil_pct": int(first["oil_pct"]),
            "extra_water_pct": float(first["extra_water_pct"]),
            "actual_moisture_pct": None,
            "actual_dry_density_g_cm3": None,
        },
        "acquisition": {
            "n_readings": int(len(rows)),
            "depth_min_cm": float(rows["depth_cm"].min()),
            "depth_max_cm": float(rows["depth_cm"].max()),
            "test_date": None,
            "lab_temperature_C": None,
            "zero_reading_N": None,
        },
        "provenance": {
            "source_file": str(first["source_file"]),
            "derived_force": derived,
        },
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tidy", type=Path, default=Path("data/processed/cpt_forces_tidy.csv"))
    parser.add_argument("--schema", type=Path, default=Path("metadata/schema/cpt_test.schema.json"))
    parser.add_argument("--out", type=Path, default=Path("metadata/tests"))
    args = parser.parse_args()

    table = pd.read_csv(args.tidy, dtype={"test_id": str})
    validator = Draft202012Validator(json.loads(args.schema.read_text(encoding="utf-8")))
    args.out.mkdir(parents=True, exist_ok=True)

    n_ok, n_bad = 0, 0
    for test_id, rows in table.groupby("test_id", sort=False):
        record = record_for(test_id, rows)
        errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        if errors:
            n_bad += 1
            print(f"REJECTED {test_id}:")
            for e in errors:
                print(f"   {'/'.join(map(str, e.path)) or '(record)'}: {e.message}")
            continue
        path = args.out / f"{test_id}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        n_ok += 1

    print(f"{n_ok} records written to {args.out}, {n_bad} rejected")


if __name__ == "__main__":
    main()
