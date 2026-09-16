# Clarifications recorded before model fitting

The original analysis_plan.json is retained. These clarifications were made during source and code review, before fitting exposure–outcome models.

- Full TIGER/Line 2023 polygons replace cartographic polygons for all point assignment. The full frame contains 23,941 tracts; 26 are absent from the cartographic file, including 25 with zero land area and one coastal tract without SVI/PLACES records. The display file is used only for maps. The anticipated eligible sample remains 23,527 tracts, subject to successful exposure retrieval.
- OSM bounding-box extraction is used because the geometry/centroid endpoints were unavailable. Nodes retain exact coordinates; other representations use the bbox midpoint. Bboxes intersecting multiple tracts or with diagonal above 200 m are flagged, with a sensitivity excluding those non-node cafes.
- The 100 m nearest-tract sensitivity concerns unmatched outer boundaries only. It does not resolve all internal boundary uncertainty.
- Unmerged counts are retained alongside the conservative same-name cross-type duplicate rule. The rule identifies candidates; it is not an independently verified establishment register.
- Seven secondary outcomes form a multiple-testing family within each model specification. Both BH and more conservative BY adjusted values are retained. No family is chosen according to the results.
- The exploratory nonlinear model is a quadratic in log2(1 + cafe density), displayed only through the observed 99th percentile.
- 2023 mental-distress estimates from the PLACES 2025 release are analyzed as a lagged-outcome sensitivity against baseline 2022 exposure and covariates. Release differences are not analyzed as temporal health trends. Kentucky/Pennsylvania missing estimates are excluded explicitly in this sensitivity.
- All model intervals condition on published PLACES point estimates and do not propagate the unavailable joint MRP estimation covariance. Global residual Moran permutation values are descriptive diagnostics.
