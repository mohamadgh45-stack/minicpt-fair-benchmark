"""Compute qc, fs and Rf, run automated quality checks, and write a QC report.

Why this script exists
----------------------
Quality control (QC) means checking data against explicit rules before using
it. Doing it in code instead of by eye has three advantages: every test gets
exactly the same checks, the rules are written down (in this file), and the
checks can be re-run whenever the data change.

Every check below produces a *flag* on a reading, never a silent deletion.
Flagged data stay in the dataset; the analysis decides what to exclude, and the
report says why. Thresholds are deliberately simple and are listed at the top so
they can be discussed and changed.

Outputs
-------
data/processed/cpt_parameters.csv  every reading with qc, fs, Rf and its flags
data/processed/test_summary.csv    one row per test, averaged over the steady zone
reports/qc_summary.csv             number of flags per test and check
reports/qc_report.md               human-readable report, incl. comparison with
                                   the thesis Table 5-2

Usage
-----
    python src/run_qc.py
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# QC rules (thresholds). Change them here, and the report will say what was used.
# ---------------------------------------------------------------------------
EXPECTED_INTERVAL_CM = 2.0        # one reading every 2 cm
EXPECTED_MAX_DEPTH_CM = 80.0
FORCE_BALANCE_TOL_N = 1.0         # |total - (tip + sleeve)| allowed
STEADY_ZONE_FROM_CM = 30.0        # above this: free-surface (critical depth) zone
SPIKE_WINDOW = 5                  # readings in the rolling median
SPIKE_REL = 0.30                  # a reading 30 % away from its local median ...
SPIKE_ABS_N = 50.0                # ... and at least 50 N away, is a spike
RF_MAX_PLAUSIBLE_PCT = 10.0       # Rf above this is physically implausible
DERIVED_SMALL_FRACTION = 0.05     # derived sleeve force < 5 % of total = low confidence

CHECKS = {
    "missing_value":       "A force value is empty",
    "irregular_depth":     "Depth step differs from 2 cm",
    "force_imbalance":     "Total force differs from tip + sleeve by more than 1 N",
    "negative_force":      "A force is negative",
    "spike_tip":           "Tip force deviates from its local median by >30 % and >50 N (checked from 6 cm, where a full window exists)",
    "rf_implausible":      "Friction ratio above 10 %",
    "derived_sleeve_small": "Sleeve force was derived by subtraction and is <5 % of total force",
    "shallow_zone":        "Reading above 30 cm, within the free-surface (critical-depth) zone",
}


def add_parameters(df: pd.DataFrame, tip_area: float, sleeve_area: float) -> pd.DataFrame:
    df = df.copy()
    df["qc_MPa"] = df["force_tip_N"] / tip_area / 1e6
    df["fs_kPa"] = df["force_sleeve_N"] / sleeve_area / 1e3
    qc_kPa = df["qc_MPa"] * 1e3
    df["Rf_pct"] = np.where(qc_kPa > 0, df["fs_kPa"] / qc_kPa * 100, np.nan)
    return df


def flag_test(g: pd.DataFrame) -> pd.DataFrame:
    """Return a boolean table: one column per check, one row per reading."""
    f = pd.DataFrame(index=g.index)
    forces = g[["force_total_N", "force_tip_N", "force_sleeve_N"]]
    measured = g["depth_cm"] > 0      # the depth-0 row is a zero placeholder

    f["missing_value"] = forces.isna().any(axis=1)
    step = g["depth_cm"].diff()
    f["irregular_depth"] = step.notna() & (step - EXPECTED_INTERVAL_CM).abs().gt(1e-9)
    f["force_imbalance"] = (g["force_total_N"] - g["force_tip_N"] - g["force_sleeve_N"]).abs() > FORCE_BALANCE_TOL_N
    f["negative_force"] = (forces < 0).any(axis=1)

    median = g["force_tip_N"].rolling(SPIKE_WINDOW, center=True, min_periods=3).median()
    dev = (g["force_tip_N"] - median).abs()
    full_window = g["depth_cm"] >= EXPECTED_INTERVAL_CM * (SPIKE_WINDOW // 2 + 1)
    f["spike_tip"] = full_window & (dev > SPIKE_ABS_N) & (dev > SPIKE_REL * median.abs())

    f["rf_implausible"] = measured & (g["Rf_pct"] > RF_MAX_PLAUSIBLE_PCT)
    f["derived_sleeve_small"] = (measured & g["derived_force"].eq("sleeve")
                                 & (g["force_sleeve_N"] < DERIVED_SMALL_FRACTION * g["force_total_N"]))
    f["shallow_zone"] = measured & (g["depth_cm"] < STEADY_ZONE_FROM_CM)
    return f


def test_level_checks(g: pd.DataFrame) -> list[str]:
    issues = []
    if len(g) != int(EXPECTED_MAX_DEPTH_CM / EXPECTED_INTERVAL_CM) + 1:
        issues.append(f"{len(g)} readings instead of {int(EXPECTED_MAX_DEPTH_CM / EXPECTED_INTERVAL_CM) + 1}")
    if g["depth_cm"].max() != EXPECTED_MAX_DEPTH_CM:
        issues.append(f"maximum depth {g['depth_cm'].max()} cm instead of {EXPECTED_MAX_DEPTH_CM}")
    zero = g.loc[g["depth_cm"] == 0, ["force_total_N", "force_tip_N", "force_sleeve_N"]]
    if not zero.empty and (zero == 0).all(axis=None):
        issues.append("depth-0 row is exactly zero: a placeholder, not a recorded zero reading")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tidy", type=Path, default=Path("data/processed/cpt_forces_tidy.csv"))
    parser.add_argument("--campaign", type=Path, default=Path("metadata/campaign.json"))
    parser.add_argument("--thesis", type=Path, default=Path("data/reference/thesis_table_5_2.csv"))
    args = parser.parse_args()

    campaign = json.loads(args.campaign.read_text(encoding="utf-8"))
    tip_area = campaign["equipment"]["tip_area_m2"]
    sleeve_area = campaign["equipment"]["sleeve_area_m2"]

    df = pd.read_csv(args.tidy, dtype={"test_id": str})
    df = add_parameters(df, tip_area, sleeve_area)

    flags = pd.concat([flag_test(g) for _, g in df.groupby("test_id", sort=False)])
    df["qc_flags"] = flags.apply(lambda r: ";".join(c for c in CHECKS if r[c]), axis=1)

    # ---- per-test summary over the steady zone, excluding problem readings ----
    exclude = flags.drop(columns=["shallow_zone"]).any(axis=1)
    usable = df[(df["depth_cm"] >= STEADY_ZONE_FROM_CM) & ~exclude]
    summary = (usable.groupby("test_id", sort=False)
               .agg(n_used=("qc_MPa", "size"), qc_mean_MPa=("qc_MPa", "mean"),
                    fs_mean_kPa=("fs_kPa", "mean"), Rf_mean_pct=("Rf_pct", "mean"))
               .round(3))
    meta = df.groupby("test_id", sort=False)[["clay_pct", "moisture_pct", "oil_pct", "extra_water_pct"]].first()
    meta["derived_force"] = df[df["depth_cm"] > 0].groupby("test_id", sort=False)["derived_force"].agg(lambda s: s.mode()[0])
    summary = meta.join(summary)

    counts = pd.DataFrame({c: flags.loc[df["test_id"] == t, c].sum() for c in CHECKS}
                          for t in summary.index)
    counts.index = summary.index
    issues = {t: test_level_checks(g) for t, g in df.groupby("test_id", sort=False)}
    status = counts.drop(columns=["shallow_zone"]).sum(axis=1).map(lambda n: "PASS" if n == 0 else "WARN")
    status[counts["force_imbalance"] > 0] = "FAIL"
    counts.insert(0, "status", status)

    # ---- comparison with the thesis table ----
    thesis = pd.read_csv(args.thesis, dtype={"test_id": str}).set_index("test_id")
    full_mean = df[df["depth_cm"] >= 0].groupby("test_id", sort=False)[["force_tip_N", "force_sleeve_N"]].mean()
    comp = thesis[["qe_MPa", "fs_kPa"]].rename(columns={"qe_MPa": "thesis_qe_MPa", "fs_kPa": "thesis_fs_kPa"})
    comp = comp.join(summary[["qc_mean_MPa", "fs_mean_kPa"]].rename(
        columns={"qc_mean_MPa": "recomputed_qc_MPa", "fs_mean_kPa": "recomputed_fs_kPa"}))
    comp["implied_tip_area_cm2"] = (full_mean["force_tip_N"] / (comp["thesis_qe_MPa"] * 1e6) * 1e4).round(2)
    comp["implied_sleeve_area_cm2"] = (full_mean["force_sleeve_N"] / (comp["thesis_fs_kPa"] * 1e3) * 1e4).round(1)

    # ---- write outputs ----
    Path("reports").mkdir(exist_ok=True)
    df.round(6).to_csv("data/processed/cpt_parameters.csv", index=False)
    summary.to_csv("data/processed/test_summary.csv")
    counts.to_csv("reports/qc_summary.csv")
    write_report(Path("reports/qc_report.md"), counts, issues, summary, comp, tip_area, sleeve_area)

    print(counts["status"].value_counts().to_string())
    print("Wrote data/processed/cpt_parameters.csv, data/processed/test_summary.csv,")
    print("      reports/qc_summary.csv and reports/qc_report.md")


def md_table(df: pd.DataFrame) -> str:
    cols = [df.index.name or ""] + list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for idx, row in df.iterrows():
        lines.append("| " + " | ".join([str(idx)] + [("" if pd.isna(v) else str(v)) for v in row]) + " |")
    return "\n".join(lines)


def write_report(path, counts, issues, summary, comp, tip_area, sleeve_area) -> None:
    ia = comp["implied_tip_area_cm2"]
    lines = [
        "# QC report — mini-CPT campaign AUT-MINICPT-2018",
        "",
        "Generated by `src/run_qc.py`. Re-run the script to regenerate this file.",
        "",
        "## Rules",
        "",
        f"qc = tip force / {tip_area:.4g} m², fs = sleeve force / {sleeve_area:.4g} m², Rf = fs / qc × 100.",
        "",
        "| Check | Rule |",
        "|---|---|",
        *[f"| `{k}` | {v} |" for k, v in CHECKS.items()],
        "",
        "Status: **FAIL** = force imbalance present; **WARN** = other flags (excluding the shallow zone); **PASS** = none.",
        "Flagged readings are kept in `cpt_parameters.csv`; the test summary uses only readings at "
        f"≥ {STEADY_ZONE_FROM_CM:g} cm without flags.",
        "",
        "## Flags per test",
        "",
        md_table(counts),
        "",
        "## Test-level findings",
        "",
    ]
    all_issues = sorted({i for iss in issues.values() for i in iss})
    for issue in all_issues:
        tests = [t for t, iss in issues.items() if issue in iss]
        who = "all tests" if len(tests) == len(issues) else ", ".join(tests)
        lines.append(f"- {issue} ({who})")
    if not all_issues:
        lines.append("- none")
    lines += [
        "",
        "## Recomputed steady-zone averages",
        "",
        md_table(summary),
        "",
        "## Comparison with thesis Table 5-2",
        "",
        "The thesis does not document how Table 5-2 was computed. `recomputed_*` are the steady-zone averages "
        "above. The implied areas are back-calculated: the area that would turn the mean force over the full "
        "depth (0–80 cm) into the published value.",
        "",
        md_table(comp),
        "",
        f"- **qc**: the implied tip area is consistent across tests ({ia.min():.1f}–{ia.max():.1f} cm², median "
        f"{ia.median():.1f} cm²), which suggests the published qe is the full-depth mean tip force divided by a "
        f"constant area of about {ia.median():.1f} cm² — not the 4.52 cm² of the 24 mm mini-cone. This is a "
        "hypothesis, not a confirmed reconstruction.",
        f"- **fs**: the implied sleeve area varies widely ({comp['implied_sleeve_area_cm2'].min():.0f}–"
        f"{comp['implied_sleeve_area_cm2'].max():.0f} cm²), so the published fs cannot be reproduced by any single "
        "rule tested here.",
        "- Lesson: processing parameters (areas, averaging range) must be stored as metadata at the time of analysis.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
