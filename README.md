# Mapped cafe availability and neighborhood context

Research data, analysis code and an interactive atlas for **Mapped cafe availability, neighborhood context and modeled mental distress in populous United States counties**.

The study covers 23,527 census tracts in 50 populous counties in the contiguous United States, with 13,195 mapped cafes and 99,313,722 ACS residents. It links the 31 December 2022 OpenStreetMap snapshot to CDC PLACES 2024 modeled health estimates and ACS 2018–2022 context.

## Revision 1.2

The atlas now supports neighborhood context layers, tract comparisons, centroid proximity measures and an algebraic association scenario. [New exploratory analyses](10_Revision_1_2/README.md) examine cafes within 500 m and 1 km of tract centroids and prediction with a 1 km separation between training and test centroids. The original sample and primary coefficients remain unchanged.

Of 17,331 tracts with no cafe mapped inside their own boundary, 3,843 (22.2%) have a mapped cafe within 1 km of their geometric centroid. A separate WGS84 geodesic calculation gives 3,839 (22.15%). These measures describe mapped proximity; they do not measure walking access, attendance or residents' actual exposure. The new analyses were developed after the original results and do not establish an intervention effect or independent health validation.

## Earlier revision 1.1

The primary sample and original coefficients are unchanged. [Additional analyses](09_Revision_1_1/README.md) quantify the cafe variable's small incremental contribution, compare historical Chicago licenses and inspection records, assess independent health-source compatibility and provide a proposed prospective study protocol. All additions are exploratory and were developed after the original results.

The audit found incomplete record concordance, and the source review did not establish independent same-year tract health validation. Statistical sensitivity checks do not resolve source-model dependence or establish effects of cafe use. See the [reviewer-concern matrix](09_Revision_1_1/methods/reviewer_response_matrix.md) for actions and remaining limitations.

## Interactive map

Open [the online interactive atlas](https://umutsimsekci.github.io/cafe-health-study/), or download `docs/index.html` and open it in a browser. All map data and D3 are embedded, so the downloaded HTML works offline. Select a county and measure, inspect or compare tracts, find an 11-digit GEOID, and export source values or scenario calculations as CSV.

The scenario evaluates the fitted regression contrast after a hypothetical change in mapped cafe availability. Its interval is conditional on the fitted coefficient and excludes source-estimation uncertainty. It is not a forecast of health changes after opening cafes. Mapped availability is not attendance or coffee consumption. Health measures are modeled area estimates, not individual diagnoses.

## Files

- `05_Data/processed/analysis_dataset.csv.gz`: compact tract-level analytical data. Preserve GEOID and county identifiers as strings.
- `05_Data/Data_Dictionary.csv`: definitions and distinction between analyzed and source-only fields.
- `05_Data/Source_Inventory.csv`: source URLs, query records and SHA-256 hashes.
- `06_Code`: original retrieval, exposure, analysis, figure and map code, with pinned dependencies and D3 license.
- `03_Tables`: numerical results underlying manuscript tables and figures.
- `07_Methods_and_Journal`: the recorded analytical plan and amendments.
- `08_Validation`: numerical, join, source and exposure checks.
- `10_Revision_1_2`: proximity and buffered prediction results, independent verification, methods and figure source data.
- `references`: study references; the original reference file is retained for version history in RIS format.

## Reproduction

See [REPRODUCE.md](REPRODUCE.md). A compact check reproduces the four primary-outcome models from the CSV. The full spatial pipeline requires the frozen raw and processed inputs in the versioned release asset `Cafe_Health_Frozen_Inputs_v1.0.0.zip`. Extract this asset into the repository root. It retains historical source responses; do not substitute current OSM businesses for the 2022 snapshot.

## Attribution and licenses

© OpenStreetMap contributors. OSM-derived data are subject to ODbL 1.0. CDC and US Census data retain their source attribution and terms. Original analysis code is MIT-licensed; embedded D3 is ISC-licensed. See [LICENSES.md](LICENSES.md).

## Research assistance and responsibility

Umut Şimşekçi and Yıldırım Cesaretli are the study authors, both at the Department of Medical Pharmacology, Gülhane Faculty of Medicine, University of Health Sciences, Ankara, Türkiye. Umut Şimşekçi led the study design, development of the interactive HTML tool and manuscript preparation. Yıldırım Cesaretli provided scientific guidance, supervision and critical review. Umut Şimşekçi is the corresponding author. The authorship arrangement and approval of the earlier manuscript were reported by the corresponding author. The expanded revision requires final scientific review by both authors before submission. The authors declare no funding or external support and no competing interests.

OpenAI Codex assisted with source identification, analytical planning, programming, numerical verification, visualization and manuscript preparation. The human authors reviewed the work and are responsible for scientific interpretation. AI tools are not authors. The repository contains actual source data and reproducible computations rather than synthetic figure values.

## Citation

Use `CITATION.cff` and the versioned GitHub release. This repository supports an unpublished manuscript and does not imply journal acceptance. No Zenodo DOI has been assigned.

The citation and authorship metadata on the main branch were updated after the v1.0.0 archive was created. The frozen v1.0.0 analytical files and release assets remain unchanged.
