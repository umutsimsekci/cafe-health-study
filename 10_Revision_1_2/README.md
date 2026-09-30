# Revision 1.2 geographical measurement checks

This revision adds centroid proximity measures, an independent geodesic sensitivity check, and a buffered version of the existing spatial prediction diagnostic. The additions were developed after the original results and are exploratory. They extend the evidence about measurement of cafe availability. They do not estimate effects of opening cafes.

The 23,527 original analytical tracts, their original cafe counts, PLACES point estimates, and primary regression specifications remain the reference sample. The new proximity measures use 17,073 nonduplicate cafe records in the complete frozen expanded extraction inventory, including mapped points in excluded or adjacent areas. The original analytical tract count sums to 13,195 cafes; the expanded inventory and the analytical sample serve different geographical purposes.

## Reproduction

Use the repository's isolated Python environment and `06_Code/requirements.txt`. Download and verify the frozen v1.0.0 release asset described in `REPRODUCE.md`, then extract it into the repository. This supplies the historical object-level assignments and the original query rectangles; the compact analysis CSV alone is insufficient for the new exposure construction.

```sh
python 10_Revision_1_2/code/strengthen_analysis.py
python 10_Revision_1_2/code/verify_proximity.py
python 10_Revision_1_2/code/make_measurement_figure.py
python 10_Revision_1_2/code/verify_results.py
```

`strengthen_analysis.py` and `verify_proximity.py` accept `--source` pointing to a directory that contains `processed` and `raw`, and `--output` for an isolated reproduction directory. `verify_results.py` accepts `--source` and `--results`. The plot script reads archived results and creates the vector PDF, 300 dpi PNG, source CSV and caption for Figure 4. Run output-generating scripts in a fresh clone or an isolated output directory so archived tables remain available for comparison.

## Measurements and results

The fixed-radius exposures count mapped cafes within 500 m or 1 km of the frozen geometric tract centroid, using EPSG:5070 planar distances. They include establishments across tract boundaries. The model exposure is `log2(1 + fixed-radius count)`, with no resident-population denominator. Accordingly its coefficients have a different scale from the primary density exposure and should not be directly compared with that coefficient.

Among 17,331 tracts with no mapped cafe inside their own boundary, 891 (5.1%) had at least one cafe within 500 m of the centroid and 3,843 (22.2%) within 1 km. Conversely, 1,409 tracts containing at least one cafe had none within 1 km of their centroid. These classifications illustrate how a tract count and centroid proximity describe different geographical quantities.

Full all-pairs enumeration independently reproduced both projected-radius counts. A WGS84 geodesic sensitivity found 3,839 zero-tract centroids with at least one cafe within 1 km, or 22.2% after rounding. Near threshold, 26 zero-tract classifications differed between distance methods. The maximum measured relative distance difference among independent nearby candidate pairs was 1.04%. Both the projected and independently constructed conservative geodesic envelopes were inside the recorded own-county extraction rectangles for all analytical centroids. The query footprint check verifies geographical extraction support, not completeness of business mapping.

New proximity regressions use the same eight contextual terms and county fixed effects as the extended primary model. The additional hospitality specification uses the count of restaurants, fast-food outlets, bars and pubs within the same radius, transformed on the same scale. County-cluster confidence intervals use CR1 correction, full design rank, and 49 degrees of freedom. The 500 m proximity model with hospitality adjustment includes zero in its interval; this is reported alongside the other specifications without selection by significance.

Buffered prediction reuses the original 20 km five-fold cell allocation. For each test fold it removes training centroids within 1 km of any test centroid across all counties. The original exposure and regression specifications are retained. The buffer separates centroids rather than whole polygons, and all test counties remain represented in training. Cafes improve pooled RMSE by 0.0042 prevalence points in the extended model and 0.0013 with hospitality adjustment. Shared PLACES construction remains present.

## Files and interpretation

`methods/exploratory_plan.json` records the analysis specifications and original plan timestamp. `methods/software_versions.json` records the execution packages. `methods/proximity_data_dictionary.csv` defines every new atlas field. `results/scientific_results.json` records source hashes and results; the separate verification files document independent checks. Descriptive county-specific slopes are provided for exploratory inspection, without county significance claims.

Centroids are geometric summaries, may not represent where residents live, and do not provide walking routes, affordability, accessibility, opening hours or attendance. OSM features retain the original node coordinates or non-node bounding-box midpoint approximation. Distances beyond 1 km refer only to the observed extraction inventory and are censored in the recommended atlas distance field. PLACES estimates are model-produced; all regression and prediction results condition on those point estimates and omit unknown joint source estimation uncertainty. Neither the proximity layers nor the coefficient illustration can evaluate a health intervention or identify benefits to cafe users.

Sources remain the December 2022 OSM snapshot, CDC PLACES 2024 estimates for 2022 selected outcomes, ACS 2018–2022 context and TIGER/Line 2023 analytical boundaries. OpenStreetMap-derived data retain ODbL 1.0 attribution and licensing; see the repository's `LICENSES.md`.
