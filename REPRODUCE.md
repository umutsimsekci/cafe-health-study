# Reproducing the analysis

## Compact primary-model check

Use Python 3.12 and install `06_Code/requirements.txt` in an isolated environment. Run:

```sh
python 06_Code/reproduce_primary.py
```

The script reads the compressed CSV, reproduces unadjusted, county-and-density, extended and hospitality-adjusted frequent mental distress models, and compares coefficients and confidence limits to the archived table. It does not rerun spatial diagnostics or exposure construction.

## Full historical reproduction

Download `Cafe_Health_Frozen_Inputs_v1.0.0.zip` from the repository's v1.0.0 release, verify it against the release SHA-256 manifest, and extract it in this directory. The asset contains `05_Data/raw` and all frozen `05_Data/processed` files, plus a file-level checksum manifest. Existing small CSV files are identical copies. The archive is approximately 1 GB uncompressed.

Run `02_prepare_health.py`, `04_build_exposures.py`, `05_analyze.py`, `06_figures.py` and `07_interactive_map.py` in order from `06_Code`. For a full boundary rebuild, first run `01_prepare_geography.py` and `01b_download_full_boundaries.py`; preserve the recorded plan, as the geography script writes a new planning record. The `00` and `03` scripts retrieve source data and should be skipped when using the frozen release. Read their service notes before attempting new downloads. Current service responses may differ from archived responses.

`09_verify_results.py` independently checks numerical results, assignment geometry and exclusions. Exact package versions are recorded in `06_Code/software_versions.json`. Spatial permutation seed: 20260915. Run output-generating scripts in a fresh clone so archived result tables remain available for comparison.

The five main figures and two supplementary figures are generated from archived observations and model outputs with Python. Manuscript authoring files are excluded because they predate later text revisions; this repository reproduces the analyses, figures and map.

## Interpretation

County-cluster and spatial uncertainty calculations condition on CDC PLACES point estimates. They do not recover unknown joint source estimation uncertainty. The study is cross-sectional and ecological. The interactive map is descriptive, not a causal simulator.
