# Mapped cafe availability and modeled health

Research data, analysis code and an interactive map for **Mapped cafe availability and modeled health in populous United States counties**.

The study covers 23,527 census tracts in 50 populous counties in the contiguous United States, with 13,195 mapped cafes and 99,313,722 ACS residents. It links the 31 December 2022 OpenStreetMap snapshot to CDC PLACES 2024 modeled health estimates and ACS 2018–2022 context.

## Interactive map

Open [the online interactive supplement](https://umutsimsekci.github.io/cafe-health-study/), or download `docs/index.html` and open it in a browser. All map data and D3 are embedded, so the downloaded HTML works offline. Select a county and measure, inspect tracts, find an 11-digit GEOID, or export the displayed data as CSV.

This is a data explorer, not a simulation of causal health effects. Mapped availability is not attendance or coffee consumption. Health measures are modeled area estimates, not individual diagnoses. The results do not establish a health benefit from using or opening cafes.

## Files

- `05_Data/processed/analysis_dataset.csv.gz`: compact tract-level analytical data. Preserve GEOID and county identifiers as strings.
- `05_Data/Data_Dictionary.csv`: definitions and distinction between analyzed and source-only fields.
- `05_Data/Source_Inventory.csv`: source URLs, query records and SHA-256 hashes.
- `06_Code`: original retrieval, exposure, analysis, figure and map code, with pinned dependencies and D3 license.
- `03_Tables`: numerical results underlying manuscript tables and figures.
- `07_Methods_and_Journal`: the recorded analytical plan and amendments.
- `08_Validation`: numerical, join, source and exposure checks.
- `references`: the 28 cited references in RIS format.

## Reproduction

See [REPRODUCE.md](REPRODUCE.md). A compact check reproduces the four primary-outcome models from the CSV. The full spatial pipeline requires the frozen raw and processed inputs in the versioned release asset `Cafe_Health_Frozen_Inputs_v1.0.0.zip`. Extract this asset into the repository root. It retains historical source responses; do not substitute current OSM businesses for the 2022 snapshot.

## Attribution and licenses

© OpenStreetMap contributors. OSM-derived data are subject to ODbL 1.0. CDC and US Census data retain their source attribution and terms. Original analysis code is MIT-licensed; embedded D3 is ISC-licensed. See [LICENSES.md](LICENSES.md).

## Research assistance and responsibility

OpenAI Codex assisted with source identification, analytical planning, programming, numerical verification, visualization and manuscript preparation. The human author reviews the work and is responsible for scientific interpretation. AI tools are not authors. The repository contains actual source data and reproducible computations rather than synthetic figure values.

## Citation

Use `CITATION.cff` and the versioned GitHub release. This repository supports a manuscript prepared for Health & Place; it does not imply acceptance or publication. No Zenodo DOI has been assigned.
