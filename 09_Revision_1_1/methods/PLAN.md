# Cafe health study revision 11

## Scope and decisions recorded before new analyses

User authorization: strengthen the four identified methodological issues, search alternatives, update the manuscript and associated submission files, references and public research archive as warranted. Umut Şimşekçi remains first and corresponding author. Existing author contributions, no funding/external support and no competing interests are retained. No journal submission, contact with third parties, participant recruitment or claim of ethics approval is authorized or implied by this revision.

This is an additional, post-results investigation. It is not preregistration. Original v10 and the frozen v1.0.0 analytical release are preserved. New analyses will be labeled exploratory/additional and all attempted specifications and source suitability decisions will be retained, irrespective of results.

1. Review alternative health sources using a compatibility matrix: independent source lineage, measurement, year, geographic identifiers, direct versus modeled estimates, survey weights/design, precision and public access. Prioritize genuinely independent direct mental-health measures. BRFSS SMART may offer a direct-estimate comparison but shares source respondents with PLACES and must not be called independent replication. A different-year or different-scale check must remain a separate estimand. Do not force mismatched data into the national tract regression.
2. Audit historical cafe records with an external administrative source that includes dated 2022 evidence, starting with Chicago food inspections in Cook County. An inspection is evidence at its recorded date, not proof of operation on 31 December or an exhaustive census. Match names and coordinates with documented rules, inspect ambiguous cases, and examine both OSM cafes and external candidate cafes not mapped in OSM. Report definition/coverage limits, socioeconomic strata, matching sensitivity, and denominators. Broaden to another compatible source when feasible.
3. On the unchanged 23,527-tract primary sample, compare county/context models with and without cafe availability. Report full and incremental R-squared, partial R-squared, RMSE, actual exposure contrasts and confidence intervals conditional on source estimates. Use independently calculated residualization to check the coefficient and contribution. Add a prespecified flexible-context check and a spatially grouped predictive check only if implementable with valid train/test separation and supported design. These are diagnostics of modeled outcomes, not independent health validation.
4. Review denominator mismatch, boundary spillover, missingness, outcome-year differences, source-model dependence, small effects, multiplicity and residual spatial dependence. Preserve prior completed checks where inputs and scope remain valid. Do not select specifications for significance. Keep fundamental residual limitations beside results.
5. Draft a separate prospective study protocol connecting access, actual use, social interaction and health. Include nonusers, repeated measurements, sampling/power strategy, confounding, clustering, consent/data minimization and required local ethics review before implementation. It is a proposed study, not completed evidence.
6. Integrate supported findings into a new English manuscript, supplementary methods and tables, figure captions/new figures as necessary, title page/cover letter, highlights, source inventory and reproducible scripts. Preserve concise varied prose. Verify all new references against primary sources and update the Zotero study collection without duplicates.
7. Validate numerical claims independently, render and inspect every changed document, check reference/citation agreement, package files and mirror to Desktop. Publish revised code/data/method metadata on GitHub with a new version when appropriate, preserve the historical release, verify links and map behavior. Do not describe remaining limitations as solved.

## Completion evidence

- Source compatibility matrix and archived metadata/query receipts.
- Historical external-record audit with inspectable matches and exclusions.
- Reproducible added analyses with independent numerical checks.
- Separate prospective protocol and revised limitations.
- Consistent revised manuscript and all affected submission/source files.
- Verified new reference records and Zotero additions.
- Visual QA, package hashes, public archive/version verification and browser check.

## Initial evidence

- No running python/git/gh processes were returned at task start.
- v10 is the current package, with Umut Şimşekçi as corresponding author.
- NYC CHS official public-use page currently lists downloadable datasets only through 2020 and says later years will be made available. Availability in reports does not establish public microdata access.
- Chicago inspection portal documents dated records from January 2010 onward; its units are inspections, with possible duplicates and time-specific findings.
