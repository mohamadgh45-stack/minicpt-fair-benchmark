"""Draw the two summary figures used in the README.

1. qc depth profiles of all 18 tests, one panel per clay content.
2. Steady-zone averages of qc against fs on log axes, with lines of constant
   friction ratio (the axes used by CPT soil-behaviour charts).

Usage
-----
    python src/make_figures.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path("reports/figures")
OIL_COLOURS = {0: "#444441", 4: "#D85A30", 8: "#378ADD"}
CLAY_MARKERS = {10: "o", 30: "s", 50: "^"}


def profiles(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 5), sharey=True)
    for ax, clay in zip(axes, (10, 30, 50)):
        sub = df[df["clay_pct"] == clay]
        for test_id, g in sub.groupby("test_id", sort=False):
            oil = int(g["oil_pct"].iloc[0])
            style = "--" if g["extra_water_pct"].iloc[0] > 0 else "-"
            ax.plot(g["qc_MPa"], g["depth_cm"], style, color=OIL_COLOURS[oil], lw=1.6, label=test_id)
        ax.axhspan(0, 30, color="#B4B2A9", alpha=0.2, lw=0)
        ax.set_title(f"{clay} % clay")
        ax.set_xlabel("qc (MPa)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, frameon=False, loc="lower left")
    axes[0].set_ylabel("depth (cm)")
    axes[0].invert_yaxis()
    fig.suptitle("Mini-CPT profiles. Colour: 0 % (grey), 4 % (orange), 8 % (blue) oil; dashed: extra water. "
                 "Shaded: free-surface zone.", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "qc_profiles.png", dpi=150)
    plt.close(fig)


def qc_fs(summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 5.5))
    fs_line = np.logspace(np.log10(20), np.log10(120), 50)
    for rf in (1, 2, 5):
        ax.plot(fs_line, fs_line / (rf * 10), color="#888780", lw=0.8, ls=":")
        ax.text(85, 85 / (rf * 10) * 1.1, f"Rf = {rf} %", fontsize=8, ha="center", color="#5F5E5A")
    for test_id, r in summary.iterrows():
        oil = int(r["oil_pct"])
        ax.scatter(r["fs_mean_kPa"], r["qc_mean_MPa"], marker=CLAY_MARKERS[int(r["clay_pct"])],
                   s=70, color=OIL_COLOURS[oil], edgecolor="white", zorder=3)
    ax.set_xlim(20, 130)
    ax.set_ylim(0.5, 10)
    ax.set_xscale("log")
    ax.set_yscale("log")
    from matplotlib.ticker import ScalarFormatter
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(ScalarFormatter())
        axis.set_minor_formatter(ScalarFormatter())
    ax.tick_params(which="minor", labelsize=7)
    ax.set_xlabel("fs (kPa)")
    ax.set_ylabel("qc (MPa)")
    ax.set_title("Steady-zone averages (≥ 30 cm, unflagged readings)\n"
                 "marker: clay 10 % ○  30 % □  50 % △ · colour: oil 0 / 4 / 8 %", fontsize=10)
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUT / "qc_vs_fs.png", dpi=150)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv("data/processed/cpt_parameters.csv", dtype={"test_id": str})
    summary = pd.read_csv("data/processed/test_summary.csv", dtype={"test_id": str}).set_index("test_id")
    profiles(df)
    qc_fs(summary)
    print(f"Figures written to {OUT}")


if __name__ == "__main__":
    main()
