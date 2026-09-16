"""Define the study sample without inspecting exposure-outcome associations."""
from pathlib import Path
import pandas as pd, geopandas as gpd, json, datetime
ROOT=Path(__file__).resolve().parents[1]; raw=ROOT/'05_Data/raw'; proc=ROOT/'05_Data/processed'
svi=pd.read_csv(raw/'svi_2022_us.csv',dtype={'FIPS':str,'STCNTY':str,'ST':str})
svi['FIPS']=svi.FIPS.str.zfill(11);svi['STCNTY']=svi.STCNTY.str.zfill(5)
# Select the 50 largest contiguous-US counties by ACS 2018-2022 resident population.
pop=svi[svi.E_TOTPOP>=0].groupby(['STCNTY','COUNTY','ST_ABBR'],as_index=False).E_TOTPOP.sum()
pop=pop[~pop.ST_ABBR.isin(['AK','HI','PR'])].sort_values(['E_TOTPOP','STCNTY'],ascending=[False,True]).head(50)
pop.to_csv(proc/'selected_counties.csv',index=False)
g=gpd.read_file(raw/'tracts_2023.zip');g['countyfips']=g.STATEFP+g.COUNTYFP
g=g[g.countyfips.isin(pop.STCNTY)].copy();g.to_parquet(proc/'study_tracts.parquet',index=False)
c=gpd.read_file(raw/'counties_2023.zip');c=c[c.GEOID.isin(pop.STCNTY)].copy();c.to_parquet(proc/'study_counties.parquet',index=False)
g[['GEOID','countyfips','ALAND','AWATER']].to_csv(proc/'tract_geography_index.csv',index=False)
print('Selected',len(pop),'counties,',len(g),'tracts; population',int(pop.E_TOTPOP.sum()))
print(pop[['STCNTY','COUNTY','ST_ABBR','E_TOTPOP']].to_string(index=False))
plan={
 'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'Analysis plan recorded before exposure-outcome model fitting; not externally preregistered.',
 'scope':'50 most populous counties in contiguous United States, ranked using summed ACS 2018-2022 total population in SVI 2022; all county census tracts, not just urban tracts.',
 'primary_period':'2022; CDC PLACES 2024 release, ACS 2018-2022 SVI 2022, OpenStreetMap snapshot 2022-12-31T23:59:59Z.',
 'primary_exposure':'Deduplicated OSM amenity=cafe mapped features per 10,000 residents; log2(1+density). This measures mapped provision, not visits or coffee intake.',
 'outcomes':['MHLTH','DEPRESSION','GHLTH','PHLTH','OBESITY','LPA','CSMOKING','DIABETES'],
 'primary_outcome':'MHLTH: model-estimated prevalence of frequent mental distress among adults.',
 'secondary_family':'Seven secondary outcomes with Benjamini-Hochberg false discovery rate adjustment; all reported.',
 'covariates':['log resident population density','poverty below 150% federal poverty level','unemployment','no high-school diploma age25+','age65+ share','age17andunder share','racial/ethnic minority share (structural context, not biological interpretation)','households without a vehicle'],
 'models':'Descriptive unadjusted; county fixed effects + log population density; extended covariate-adjusted model; additional noncafe hospitality density sensitivity. County-cluster robust uncertainty, finite-cluster t reference. Estimates are descriptive ecological associations conditional on modeled outcomes, not causal effects.',
 'sensitivity':['per square kilometre density','cafe presence','exclude top 1% exposure','population-weighted model','leave-one-county-out estimates','spatial dependence diagnostics and spatial-HAC sensitivity','OSM node-only definition','2023 health estimates where available with explicit temporal limitations'],
 'eligibility':'Resident population >=500, positive land area; complete primary model variables; per-outcome missingness audited. OSM extraction failures never coded as zero.',
 'quality':'Unique geography identifiers, one-to-one merges, missing/sentinel audit, OSM duplicate audit, point assignment and boundary sensitivity, source hashes and software versions.',
 'interpretation':'PLACES regression outcomes are modeled using demographic and contextual predictors. Adjustment cannot restore unobserved individual health measurements. OSM missingness and unequal mapping intensity are unresolved measurement error. Cross-sectional associations cannot establish cause or benefits of cafe openings.',
}
(ROOT/'07_Methods_and_Journal/analysis_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
