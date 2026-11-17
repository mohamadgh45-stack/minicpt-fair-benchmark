# Measurement protocol for laboratory mini-CPT campaigns — v1.0

This protocol is written in hindsight. It describes how the 2017–2018 campaign
*should* have been run and recorded, based on what was missing when the data
were reprocessed in 2026. Each rule names the gap it closes.

## 1. Before the campaign

| # | Rule | Gap it closes |
|---|---|---|
| 1.1 | Write a test matrix: every condition, its code, and the number of **replicates** (at least 3 per condition). | One test per condition; scatter could not be separated from the effect of oil. |
| 1.2 | Define the test-code format and store the decoding rule with the data. | The meaning of a fourth number in codes like `10.5.4.4` had to be inferred from the thesis text. |
| 1.3 | Record cone diameter, sleeve length and the resulting areas as metadata. | The thesis results imply an area that does not match the 24 mm cone. |
| 1.4 | Calibrate each load cell; store the calibration factor, date and certificate. | No calibration record survives. |
| 1.5 | State the rationale for each fixed parameter (e.g. 24 h equilibration because the standard requires at least X h for this soil class). | Values without reasons cannot be judged or reused. |

## 2. Sample preparation (per test)

| # | Record | Why |
|---|---|---|
| 2.1 | Mass of each component (sand 141, sand 191, kaolinite, water, oil) | Allows the actual mix to be checked against the target |
| 2.2 | Start and end time of equilibration | Time is a variable even when it is meant to be fixed |
| 2.3 | Height of each 5 cm layer at four corners | In-process QC of uniform density |
| 2.4 | Actual moisture content (oven, with the oil-evaporation correction stated) and actual dry density | Target and actual values differ |
| 2.5 | Laboratory temperature | Oil viscosity depends on temperature |

## 3. Penetration (per test)

| # | Rule | Why |
|---|---|---|
| 3.1 | Record a **zero reading** of every channel before penetration, as a real measurement. | The depth-0 rows in the thesis data are typed zeros. |
| 3.2 | Keep the **raw logger file** unchanged; never overwrite it with edited values. | Only chart workbooks survived; original logger files are lost. |
| 3.3 | Record which channels are measured and which are derived (e.g. sleeve = total − tip). | The derivation method changed between test series without being documented. |
| 3.4 | Log the actual penetration rate from the logger time stamps, not only the set point. | Rate is the main confounding variable in CPT. |

## 4. Processing

| # | Rule | Why |
|---|---|---|
| 4.1 | All processing in scripts under version control; no manual edits in spreadsheets. | Test 30.12.8 contains hand-typed values where total ≠ tip + sleeve. |
| 4.2 | Store every processing parameter (areas, averaging depth range, exclusion rules) in the output metadata. | The thesis Table 5-2 cannot be reproduced. |
| 4.3 | Exclude the free-surface zone (here: above 30 cm, ≈ 12 cone diameters) from averages, and say so. | Averages over 0–80 cm mix the shallow build-up with steady penetration. |
| 4.4 | Run automated QC (`src/run_qc.py`) and keep flagged values, with their flags, rather than deleting them. | Problems remain visible and decisions remain reviewable. |

## 5. Transfer to GPR surveys at the Utility Mapping Site

The same logic applies; only the instrument changes.

| CPT campaign | GPR benchmark |
|---|---|
| Penetration rate held at 20 mm/s | Survey speed, trace spacing and time window fixed per protocol |
| Soil mix and moisture recorded per test | Soil type per site; volumetric moisture and conductivity per survey day |
| Zero reading per channel | Time-zero and system calibration per survey |
| Raw logger file kept unchanged | Raw radargram files kept unchanged, with checksums |
| Replicates per condition | Repeated lines with the same device on the same day (repeatability) and across devices and seasons (reproducibility) |
| Known soil composition | Known pipe positions (ground truth) for scoring detection and position error |

A draft metadata schema for GPR survey lines is in `docs/gpr_line.schema.json`.
