# Data management plan

## What the data are

| Item | Format | Location |
|---|---|---|
| Original workbooks embedded in the thesis | `.xlsx`, unchanged | `data/raw/thesis_embedded/` |
| Checksums of the original files | CSV (SHA-256) | `data/raw/thesis_embedded/MANIFEST.csv` |
| Values transcribed from the thesis | CSV | `data/reference/` |
| Tidy forces with cell-level provenance | CSV | `data/processed/cpt_forces_tidy.csv` |
| qc, fs, Rf and QC flags per reading | CSV | `data/processed/cpt_parameters.csv` |
| Per-test averages | CSV | `data/processed/test_summary.csv` |
| Campaign and per-test metadata, schema | JSON, JSON Schema | `metadata/` |
| QC report and figures | Markdown, PNG | `reports/` |

## Rules

1. **Raw is read-only.** Files in `data/raw/` are never edited. Their checksums
   in `MANIFEST.csv` let anyone verify this.
2. **Everything else is generated.** `data/processed/`, `metadata/tests/` and
   `reports/` can be deleted and rebuilt by running the scripts in `src/` in
   the order given in the README.
3. **Open formats.** CSV and JSON, readable without proprietary software.
   Units are part of column names (`force_tip_N`, `qc_MPa`).
4. **Unknown is explicit.** Missing information is written as `null` with a
   note, never guessed or left out.
5. **Flags, not deletions.** QC marks problem values; it does not remove them.
6. **Version control.** All code, metadata and processed data are tracked in
   Git; every change has an author, date and message.

## Naming

- Tests keep their original codes: `clay.moisture.oil[.extra water]`, in percent.
- Files are lowercase with underscores; units are SI-based and written in names.

## Sharing and licence

- Code: MIT licence.
- Data and documentation: CC BY 4.0. Cite the MSc thesis (Ghalenooee, 2019,
  Amirkabir University of Technology) and this repository.
- Planned: archive a tagged release on Zenodo to obtain a DOI.

## Known limitations

- Original logger files are lost; the workbooks embedded in the thesis are the
  earliest surviving copy.
- Calibration factors, zero readings, test dates, actual moisture and density
  were not recorded.
- One test per condition; repeatability cannot be estimated.
