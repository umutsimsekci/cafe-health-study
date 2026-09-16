"""Describe analytical variables, source-only fields and derived quantities."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
d=pd.read_parquet(ROOT/'05_Data/processed/analysis_with_predictions.parquet')
health={'MHLTH':'Frequent mental distress, 14+ mentally unhealthy days in the preceding 30 days','DEPRESSION':'Ever told by a health professional that the adult had a depressive disorder','GHLTH':'Fair or poor self-rated health','PHLTH':'Frequent physical distress, 14+ physically unhealthy days in the preceding 30 days','OBESITY':'Obesity, body mass index at least 30 kg/m²','LPA':'No leisure-time physical activity in the preceding month','CSMOKING':'Current smoking','DIABETES':'Diagnosed diabetes, excluding diabetes only during pregnancy'}
specific={
'GEOID':('11-character Census tract geographic identifier; retain leading zeros','identifier','Census TIGER/Line 2023','join key'),
'countyfips':('5-character county or county-equivalent identifier','identifier','Derived from GEOID','county fixed effect and cluster'),
'E_TOTPOP':('ACS 2018–2022 resident population estimate','persons','CDC/ATSDR SVI 2022','exposure denominator and eligibility'),
'EP_POV150':('Persons below 150% of the federal poverty threshold, among persons for whom poverty status is determined','percent','SVI 2022 / ACS S1701','primary covariate'),
'EP_UNEMP':('Unemployment rate; ACS DP03_0009PE','percent','SVI 2022 / ACS DP03','primary covariate'),
'EP_NOHSDP':('Persons aged 25+ without a high-school diploma','percent','SVI 2022 / ACS S0601','primary covariate'),
'EP_AGE65':('Resident population aged 65 or older','percent','SVI 2022 / ACS','primary covariate'),
'EP_AGE17':('Resident population aged 17 or younger','percent','SVI 2022 / ACS','primary covariate'),
'EP_MINRTY':('SVI racial/ethnic minority share, encompassing all residents except non-Hispanic White alone; structural context, not biological interpretation','percent','SVI 2022 / ACS','primary covariate'),
'EP_NOVEH':('Households with no vehicle available','percent','SVI 2022 / ACS DP04','primary covariate'),
'TotalPop18plus':('Adult population supplied by PLACES; distinct from the ACS resident denominator','persons','PLACES 2024','sensitivity model weights'),
'TotalPopulation':('Population supplied by PLACES, retained for source traceability; not cafe-density denominator','persons','PLACES 2024','source only'),
'ALAND':('Census land area','m²','TIGER/Line 2023','land-density derivation'),
'AWATER':('Census water area','m²','TIGER/Line 2023','source only'),
'land_km2':('ALAND / 1,000,000','km²','Derived','eligibility and alternative denominator'),
'pop_density':('E_TOTPOP / land_km2','residents/km²','Derived','population density'),
'log_pop_density':('log2(pop_density)','log2 residents/km²','Derived','primary covariate'),
'cafe_log':('log2(1 + cafe_per_10k); a one-unit contrast doubles one plus density','log2(1+density)','Derived','primary exposure'),
'noncafe_log':('log2(1 + noncafe_per_10k)','log2(1+density)','Derived','hospitality sensitivity'),
'cafe_present':('At least one qualifying mapped cafe','0/1','Derived','presence sensitivity'),
'primary_fitted':('Fitted primary-model frequent mental-distress prevalence','percent','Primary regression','diagnostic'),
'primary_residual':('Observed PLACES point estimate minus primary fitted value','percentage points','Primary regression','diagnostic'),
'geometry':('Full-resolution Census tract polygon in the GeoParquet CRS metadata; not simplified map geometry','polygon','TIGER/Line 2023','analytical geometry'),
'x_m':('Full tract polygon centroid easting','metres, EPSG:5070','Derived','spatial calculations'),
'y_m':('Full tract polygon centroid northing','metres, EPSG:5070','Derived','spatial calculations'),
'longitude':('Full tract polygon centroid longitude','degrees, EPSG:4326','Derived','location'),
'latitude':('Full tract polygon centroid latitude','degrees, EPSG:4326','Derived','location')}
rows=[]
for col in d.columns:
 if col in specific:desc,unit,source,role=specific[col]
 elif col.endswith(('CrudePrev','Crude95CI','_lower','_upper')):
  key=col.split('_')[0];desc=health.get(key,key+'; see CDC release measure dictionary')
  desc+= '; published 95% confidence interval' if col.endswith('Crude95CI') else ('; published lower 95% confidence bound' if col.endswith('_lower') else ('; published upper 95% confidence bound' if col.endswith('_upper') else '; modeled crude adult prevalence'))
  unit='percent';source='CDC PLACES 2024';role=('primary outcome' if key=='MHLTH' else 'secondary outcome') if key in health else 'source only; not analyzed in this study'
 elif col.endswith('_count'):
  desc=col.replace('_',' ')+'; qualifying mapped features assigned to the tract'
  if 'node' in col:desc+='; node objects only'
  if 'unmerged' in col:desc+='; before cross-type candidate-duplicate removal'
  if '100m' in col:desc+='; also nearest assignment of otherwise unassigned cafes within 100 m'
  if 'unambiguous' in col:desc+='; excludes non-node bboxes spanning tracts or exceeding 200 m diagonal'
  if col=='noncafe_count':desc+='; sum of restaurant, fast_food, bar and pub'
  unit='count';source='OSM snapshot 2022-12-31 via ohsome';role='exposure or sensitivity'
 elif col.endswith('per_10k'):
  desc='10,000 times corresponding mapped feature count / E_TOTPOP';unit='mapped features per 10,000 residents';source='OSM and ACS, derived';role='exposure or sensitivity'
 elif col=='cafe_per_km2':desc='cafe_count / land_km2';unit='mapped cafes/km²';source='OSM and Census, derived';role='alternative exposure'
 elif col.startswith('exclude_') or col=='included':desc=col.replace('_',' ')+'; eligibility flag';unit='boolean';source='Derived';role='sample flow'
 elif col.endswith('_join'):desc='One-to-one merge status: both or left_only';unit='category';source='Join audit';role='data quality'
 else:desc=col+'; unchanged source field retained for traceability';unit='source-specific';source='Census, SVI or PLACES as identified in raw source files';role='identifier or source only'
 rows.append({'variable':col,'description':desc,'units':unit,'source':source,'role':role,'missing_in_analysis':int(d[col].isna().sum())})
pd.DataFrame(rows).to_csv(ROOT/'05_Data/Data_Dictionary.csv',index=False)
(ROOT/'05_Data/README.md').write_text('''# Data and licensing notes

The raw folder contains frozen public source responses and their provenance files. The processed folder contains one row per tract and a separate object-level OSM assignment file. Data_Dictionary.csv identifies analyzed fields and source-only columns; additional PLACES indicators are retained without being analyzed.

Use analysis_dataset.csv for non-spatial reanalysis and the matching GeoParquet for geography. all_tracts_and_exclusions.csv includes the complete sample frame. analysis_with_predictions.parquet adds primary fitted values and residuals. All identifiers must remain strings. SVI -999 sentinels were treated as missing. Empty cells mean missing, not zero. Cafe counts of zero follow successful geographical extraction.

Reference periods: OSM snapshot 31 December 2022; selected health indicators use 2022 BRFSS in PLACES 2024; contextual measures pool ACS 2018–2022; boundaries are TIGER/Line 2023. PLACES 2025 is used only for the specified 2023-outcome sensitivity. Source fields outside the eight declared outcomes may have different reference periods and were not interpreted here.

© OpenStreetMap contributors. OSM-derived databases are subject to ODbL 1.0 and attribution: https://www.openstreetmap.org/copyright and https://opendatacommons.org/licenses/odbl/1-0/ . The combined research package does not replace underlying source licenses. Retain these notices with exports. CDC and US Census files retain their source attribution. D3 code is under ISC; its license accompanies the bundled code.

Published health confidence limits concern the original tract estimates. Regression confidence intervals condition on their point estimates and do not include the unknown covariance of original estimation errors. There are no individual health or cafe-attendance records in this package.
''',encoding='utf8')
print('DATA DICTIONARY',len(rows),'fields')
