# Offline research atlas, version 1.2.0

Open `docs/index.html` directly in a modern browser or use the repository's
GitHub Pages URL. The whole app, tract dataset, simplified polygons and D3
7.9.0 are embedded in the HTML. No server, external tiles, tracking or live
source queries are required. The HTML is approximately 22 MB; the initial load
includes parsing all 23,527 tract records.

The atlas follows the study's frozen source vintages: OpenStreetMap at the end
of 2022, CDC PLACES 2024 release with the analyzed outcomes based on 2022 BRFSS,
and ACS 2018–2022 context. It covers the analytical complete-case sample in 50
populous counties, rather than the whole United States. Source properties keep
their original precision. Geometry is simplified by 80 m for display, and
coordinates are rounded to six decimals; it is not the analytical geometry.

## Added features

- Fourteen source or joint-pattern layers: three own-tract cafe measures; three
  centroid-proximity cafe counts; three modeled health outcomes; four
  neighborhood context measures; one joint cafe/mental-distress view.
- County selection, exact GEOID search, a tract selector and previous/next
  navigation provide mouse and keyboard access. A selected tract is highlighted
  and its source values are retained in the profile.
- A reference tract can be held for a two-tract comparison while selecting
  another tract, including in another county.
- Fixed study-wide source color limits permit comparisons between counties.
  An unweighted histogram shows the distribution in the displayed tracts; dark
  and orange lines locate the selected and reference tracts. Values beyond the
  color limits are collected into edge bars; CSV and profiles retain their
  exact values.
- CSV exports include source vintages, OSM attribution/license terms, unchanged string identifiers and
  text-prefixed identifier columns for spreadsheet imports. Source `GEOID` and
  `countyfips` columns must be imported as text to preserve leading zeros.

The 500 m and 1,000 m proximity layers describe straight-line distances from
the full-resolution tract polygon centroid to retained cafes from the frozen,
expanded source extracts. Nearby cafes may be in adjacent or excluded tracts.
Source extraction coverage was independently checked for every centroid's
1 km neighborhood. Centroid proximity is distinct from own-tract counts,
residential exposure, routes, walking time, attendance and individual access.
It also does not remove errors or omissions in the OSM source.

The joint-pattern view uses a separate zero-cafe category, then splits positive
cafe density at its pooled median. Mental distress is split at pooled thirds.
These descriptive categories do not represent covariate-adjusted comparisons.

## Association scenarios

The scenario colors displayed tracts with a conditional contrast in the fitted
cafe term:

```
contrast = beta * (log2(1 + target_density) - log2(1 + baseline_density))
```

Density is mapped cafes per 10,000 ACS residents. The user chooses either the
neighborhood-context adjusted coefficient or the coefficient additionally
adjusted for non-cafe hospitality. Inputs add/remove an integer number of
mapped cafes in each tract (bounded at zero), or multiply existing density by
a percentage change. A percentage multiplier leaves zero-density tracts at
zero and does not specify integer new establishments.

The result is in percentage points. It is never added to a PLACES estimate and
does not generate a new predicted health prevalence. It does not forecast the
effect of opening/closing cafes or identify an intervention benefit. County
and neighborhood terms are held fixed, and the assumptions cannot be tested
by manipulating the interface.

Coefficient-only intervals multiply the archived county-clustered 95% cafe
coefficient limits by the exposure contrast. Endpoints are sorted when the
contrast is negative. These intervals omit unknown joint PLACES estimation
uncertainty, mapping error, individual variation and intervention uncertainty.
The interface reports the cafe term's small incremental R². Independent,
observed same-year tract health validation has not been established.

Targets beyond the pooled observed density range are hatched and withheld from
scenario coloring and numerical contrast exports. Their target density and
support flags remain exportable. Targets above the observed 99th percentile are
flagged as sparsely represented. This one-dimensional support check is not a
test of joint covariate support or transportability. Scenario color limits are
symmetric and computed across supported study tracts for the current input;
they remain unchanged when selecting another county.

## Rebuild and checks

Extract the existing frozen-input release into the repository root as described
in `REPRODUCE.md`, then run:

```sh
python 06_Code/build_atlas.py
node 06_Code/test_atlas.js
```

The builder defaults to `05_Data/processed`, writes `docs/index.html` and
`docs/atlas_manifest.json`, and enables the proximity layers when
`10_Revision_1_2/results/nearby_cafe_exposure.csv` is available. The legacy
`python 06_Code/07_interactive_map.py` command delegates to this builder.
Alternate paths can be supplied without modifying source data:

```sh
python 06_Code/build_atlas.py --processed-root /path/to/frozen/processed \
  --nearby-csv /path/to/nearby_cafe_exposure.csv \
  --output /path/to/index.html \
  --anonymous-output /path/to/Cafe_Health_Research_Atlas_Anonymous.html
```

The anonymous edition has identical functionality and source values but omits
the repository link. The manifest records input/output SHA-256 fingerprints,
sample totals, data joins, geometry transformations, embedded property
precision and exact scenario coefficients.

`test_atlas.js` reads the actual embedded dataset and configuration. It checks
sample and cafe/population totals, string identifiers, all-tract exposure
consistency, every tract's zero-change scenarios, addition/removal and
percentage contrasts, reversed confidence endpoints, clipping, extrapolation,
missing-value handling and proximity counts. These are numerical and data
integrity checks. Browser interaction and responsive-layout review are separate
checks.

OSM-derived data retain ODbL attribution and terms; analysis code is
MIT-licensed and the embedded D3 library is ISC-licensed. See `LICENSES.md`.
