from pathlib import Path
import pandas as pd,numpy as np,geopandas as gpd,json
ROOT=Path(__file__).resolve().parents[1];raw=ROOT/'05_Data/raw';proc=ROOT/'05_Data/processed'
g=gpd.read_parquet(proc/'study_tracts_full_resolution.parquet')
s=pd.read_csv(raw/'svi_2022_us.csv',dtype={'FIPS':str,'STCNTY':str});s.FIPS=s.FIPS.str.zfill(11)
svcols=['FIPS','E_TOTPOP','EP_POV150','EP_UNEMP','EP_NOHSDP','EP_AGE65','EP_AGE17','EP_MINRTY','EP_NOVEH','EP_AFAM','EP_HISP','EP_ASIAN','E_DAYPOP']
s=s[svcols].copy()
for k in svcols[1:]:s[k]=pd.to_numeric(s[k],errors='coerce').replace(-999,np.nan)
p=pd.read_csv(raw/'places_2024.csv',dtype={'TractFIPS':str,'CountyFIPS':str});p.columns=p.columns.str.strip();p.TractFIPS=p.TractFIPS.str.zfill(11)
cols=['TractFIPS','StateAbbr','CountyName','TotalPopulation','TotalPop18plus']+[x for x in p.columns if x.endswith(('CrudePrev','Crude95CI'))]
assert p.TractFIPS.is_unique and s.FIPS.is_unique and g.GEOID.is_unique
d=g.merge(s,left_on='GEOID',right_on='FIPS',how='left',validate='one_to_one',indicator='svi_join').merge(p[cols],left_on='GEOID',right_on='TractFIPS',how='left',validate='one_to_one',indicator='places_join')
for k in ['MHLTH','DEPRESSION','GHLTH','PHLTH','OBESITY','LPA','CSMOKING','DIABETES']:
 bounds=d[k+'_Crude95CI'].str.extract(r'\(\s*([\d.]+),\s*([\d.]+)\)')
 d[k+'_lower']=pd.to_numeric(bounds[0]);d[k+'_upper']=pd.to_numeric(bounds[1])
 assert ((d[k+'_lower']<=d[k+'_CrudePrev'])|(d[k+'_CrudePrev'].isna())).all()
 assert ((d[k+'_upper']>=d[k+'_CrudePrev'])|(d[k+'_CrudePrev'].isna())).all()
d['land_km2']=d.ALAND/1e6;d['pop_density']=d.E_TOTPOP/d.land_km2
cent=d.to_crs(5070).geometry.centroid;d['x_m']=cent.x;d['y_m']=cent.y
ll=gpd.GeoSeries(cent,crs=5070).to_crs(4326);d['longitude']=ll.x;d['latitude']=ll.y
d.to_parquet(proc/'health_geography.parquet',index=False)
audit={'tracts_in_selected_counties':len(d),'unique_geoid':bool(d.GEOID.is_unique),'svi_join':d.svi_join.value_counts().to_dict(),'places_join':d.places_join.value_counts().to_dict(),'population_below_500':int((d.E_TOTPOP<500).sum()),'nonpositive_land_area':int((d.land_km2<=0).sum()),'missing_covariates':d[svcols[1:]].isna().sum().to_dict(),'health_missing':{k:int(d[k+'_CrudePrev'].isna().sum()) for k in ['MHLTH','DEPRESSION','GHLTH','PHLTH','OBESITY','LPA','CSMOKING','DIABETES']}}
(ROOT/'08_Validation/base_data_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf8');print(json.dumps(audit,indent=2))
