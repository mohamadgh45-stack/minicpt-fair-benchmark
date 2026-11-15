"""Turn the thesis CPT workbooks into one tidy table: one row per test per depth.

Why this script exists
----------------------
In the thesis workbooks, each sheet holds six tests side by side: a test code
in one header row, then three columns (Total, Tip, Side force in newtons) per
test, and one row per 2 cm of depth. That layout is good for charts in Word but
bad for analysis.

"Tidy" data follows three rules:
  1. each variable is a column,
  2. each observation is a row,
  3. each value is a cell.
Here one observation = one test at one depth.

The script also records, for every row:
  * the exact source file and cells the numbers came from (provenance),
  * which of the three forces was not typed in but calculated by an Excel
    formula from the other two ("derived_force"). This differs between tests,
    so it must be recorded rather than assumed.
It also decodes the test code into its parts.

Usage
-----
    python src/build_tidy.py
"""

import argparse
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# Which embedded workbook holds which mixture. This mapping was established by
# opening each workbook; it is knowledge about the data, so it is written down
# here instead of being kept in someone's head.
CPT_WORKBOOKS = {
    "Microsoft_Excel_Worksheet5.xlsx": 10,   # % clay
    "Microsoft_Excel_Worksheet7.xlsx": 30,
    "Microsoft_Excel_Worksheet9.xlsx": 50,
}
# Worksheets 6, 8 and 10 contain the same values as 5, 7 and 9
# (each chart in the thesis embeds its own copy), so they are not read again.


def decode_test_code(code: str) -> dict:
    """'30.12.4' -> clay 30 %, moisture 12 %, oil 4 %, extra water 0 %.
    '10.5.4.4' -> the fourth number is extra water added after the oil."""
    parts = [float(p) for p in code.split(".")]
    if len(parts) not in (3, 4):
        raise ValueError(f"Unexpected test code: {code!r}")
    return {
        "clay_pct": parts[0],
        "moisture_pct": parts[1],
        "oil_pct": parts[2],
        "extra_water_pct": parts[3] if len(parts) == 4 else 0.0,
    }


FORCE_NAMES = ("total", "tip", "sleeve")


def derived_force(formula_row: tuple, col: int) -> str:
    """Return which of the three force cells holds an Excel formula, if any."""
    found = [name for name, cell in zip(FORCE_NAMES, formula_row[col:col + 3])
             if isinstance(cell, str) and cell.startswith("=")]
    return ",".join(found) if found else "none"


def read_cpt_workbook(path: Path, expected_clay: float) -> list[dict]:
    # Open the workbook twice: once for the calculated values, once for the
    # formulas themselves, so we can tell typed numbers from derived ones.
    rows = list(load_workbook(path, data_only=True).active.iter_rows(values_only=True))
    formula_rows = list(load_workbook(path, data_only=False).active.iter_rows(values_only=True))

    # Find the header row: the one whose column B says 'Depth(cm)'.
    header_index = next(i for i, r in enumerate(rows) if r[1] == "Depth(cm)")
    header = rows[header_index]
    data_rows = rows[header_index + 2:]   # skip the units row (Total/Tip/Side)

    records = []
    for col in range(2, len(header), 3):  # C, F, I, ... : first column of each test
        test_id = header[col]
        if test_id is None:
            continue
        test_id = str(test_id).strip()
        decoded = decode_test_code(test_id)
        if decoded["clay_pct"] != expected_clay:
            raise ValueError(f"{path.name}: test {test_id} does not match {expected_clay} % clay")

        for offset, row in enumerate(data_rows):
            depth = row[1]
            if depth is None:          # end of the data block
                break
            excel_row = header_index + 3 + offset   # openpyxl rows start at 1
            formula_row = formula_rows[header_index + 2 + offset]
            records.append({
                "test_id": test_id,
                **decoded,
                "depth_cm": depth,
                # round(..., 6) removes floating-point noise such as
                # 455.46499999999 -> 455.465 without changing real precision
                "force_total_N": round(row[col], 6),
                "force_tip_N": round(row[col + 1], 6),
                "force_sleeve_N": round(row[col + 2], 6),
                "derived_force": derived_force(formula_row, col),
                "source_file": path.name,
                "source_cells": f"{get_column_letter(col + 1)}{excel_row}:"
                                f"{get_column_letter(col + 3)}{excel_row}",
            })
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=Path("data/raw/thesis_embedded"))
    parser.add_argument("--out", type=Path, default=Path("data/processed/cpt_forces_tidy.csv"))
    args = parser.parse_args()

    records = []
    for filename, clay in CPT_WORKBOOKS.items():
        records += read_cpt_workbook(args.raw / filename, clay)

    table = pd.DataFrame(records)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out, index=False)

    print(f"Wrote {len(table)} rows for {table['test_id'].nunique()} tests to {args.out}")
    print("\nWhich force was calculated by a formula, per test (number of depths):")
    print(table.groupby(["test_id", "derived_force"], sort=False).size().to_string())


if __name__ == "__main__":
    main()
