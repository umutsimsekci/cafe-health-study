"""Full TIGER/Line polygons for point assignment; cartographic geometry for display."""
from pathlib import Path
import requests,json,datetime,hashlib,concurrent.futures
import geopandas as gpd,pandas as pd
ROOT=Path(__file__).resolve().parents[1];raw=ROOT/'05_Data/raw/tiger_full';raw.mkdir(exist_ok=True);proc=ROOT/'05_Data/processed'
chosen=pd.read_csv(proc/'selected_counties.csv',dtype={'STCNTY':str});codes=set(chosen.STCNTY);states=sorted({x[:2] for x in codes})
def fetch(state):
 url=f'https://www2.census.gov/geo/tiger/TIGER2023/TRACT/tl_2023_{state}_tract.zip';p=raw/(state+'.zip')
 if not p.exists():
  r=requests.get(url,timeout=(25,240));r.raise_for_status();p.write_bytes(r.content)
 b=p.read_bytes();(raw/(state+'.source.json')).write_text(json.dumps({'url':url,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2))
 g=gpd.read_file(p);g['countyfips']=g.STATEFP+g.COUNTYFP;g=g[g.countyfips.isin(codes)].copy()
 print('TIGER',state,len(g),len(b),flush=True);return g
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:parts=list(ex.map(fetch,states))
g=gpd.GeoDataFrame(pd.concat(parts,ignore_index=True),crs=parts[0].crs)
cart=gpd.read_parquet(proc/'study_tracts.parquet');assert set(cart.GEOID).issubset(set(g.GEOID))
extra=g[~g.GEOID.isin(cart.GEOID)].drop(columns='geometry')
extra.to_csv(ROOT/'08_Validation/full_tracts_absent_from_cartographic_file.csv',index=False)
assert g.GEOID.is_unique;assert g.geometry.notna().all()
g.to_parquet(proc/'study_tracts_full_resolution.parquet',index=False)
print('FULL GEOMETRY COMPLETE',len(g),flush=True)
