# Revision 1.1 exploratory validation and model diagnostics

This directory supplements the unchanged 23,527-tract analysis with post-results investigations. Plans were recorded before the additional computations, not before the original findings. See `methods` for dates, rules and the reviewer-concern matrix.

## Main findings

- Adding cafe availability increased extended-model R² by 0.000736 and hospitality-model R² by 0.000247. Partial R² values were 0.004754 and 0.001605. These are conditional model diagnostics, not health benefits.
- The observed interquartile exposure contrast corresponded to −0.126 and −0.085 prevalence percentage points, respectively.
- Five-km spatially grouped prediction reduced RMSE by 0.0037 and 0.0011 prevalence points. Full fold assignments and 20-km results are included.
- Chicago linkage connected 269 of 742 mapped cafes to temporally eligible licenses within 100 m under fixed name rules. In the reverse coffee-named subset, 157 of 281 licenses linked to an OSM cafe. These are concordance yields, not national completeness or business-validity estimates.
- The targeted alternative-health-source review did not establish an independent same-year, same-measure tract comparison. The protocol is a proposed follow-up, with no participant data or ethics approval claimed.

## Reproduce

Use the Python environment described in the repository root. From the root run:

```sh
python 09_Revision_1_1/code/additional_models.py
```

The script uses the compressed analytical CSV already in the repository when an uncompressed CSV is absent. For the historical audit, first extract the original frozen-input asset from release v1.0.0 into the repository root. It supplies the OSM object file and full analytical tract geometry. Then run:

```sh
python 09_Revision_1_1/code/chicago_audit.py
python 09_Revision_1_1/code/verify_new_results.py
python 09_Revision_1_1/code/make_new_figures.py
```

Run in a fresh checkout: scripts regenerate the archived `results` files. Verify numerical values against the frozen release before replacing outputs. No new network requests are needed for reproduction.

## Source receipts and limits

The `sources` directory retains City of Chicago data retrieved 16 September 2026, the NYC 2026 profile workbook and bibliographic metadata. Each raw response has a source receipt with query, retrieval timestamp and SHA-256. City data are attributed to the City of Chicago and remain subject to the portal's terms of use. The records are retrospective administrative releases and may have been updated since 2022. The boundary was current at retrieval, not reconstructed historically. Their inclusion does not imply agency endorsement.

OSM-derived results retain ODbL attribution. No cited research-article PDFs, author manuscripts, journal submission materials, credentials or participant records are included. Data-source notices are in the root LICENSES.md.
