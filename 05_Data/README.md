# Data and licensing notes

The raw folder contains frozen public source responses and their provenance files. The processed folder contains one row per tract and a separate object-level OSM assignment file. Data_Dictionary.csv identifies analyzed fields and source-only columns; additional PLACES indicators are retained without being analyzed.

Use analysis_dataset.csv for non-spatial reanalysis and the matching GeoParquet for geography. all_tracts_and_exclusions.csv includes the complete sample frame. analysis_with_predictions.parquet adds primary fitted values and residuals. All identifiers must remain strings. SVI -999 sentinels were treated as missing. Empty cells mean missing, not zero. Cafe counts of zero follow successful geographical extraction.

Reference periods: OSM snapshot 31 December 2022; selected health indicators use 2022 BRFSS in PLACES 2024; contextual measures pool ACS 2018–2022; boundaries are TIGER/Line 2023. PLACES 2025 is used only for the specified 2023-outcome sensitivity. Source fields outside the eight declared outcomes may have different reference periods and were not interpreted here.

© OpenStreetMap contributors. OSM-derived databases are subject to ODbL 1.0 and attribution: https://www.openstreetmap.org/copyright and https://opendatacommons.org/licenses/odbl/1-0/ . The combined research package does not replace underlying source licenses. Retain these notices with exports. CDC and US Census files retain their source attribution. D3 code is under ISC; its license accompanies the bundled code.

Published health confidence limits concern the original tract estimates. Regression confidence intervals condition on their point estimates and do not include the unknown covariance of original estimation errors. There are no individual health or cafe-attendance records in this package.
