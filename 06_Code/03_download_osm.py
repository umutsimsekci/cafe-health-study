"""Download timestamped public OSM bounding-box features; resumable by county.

ohsome v1 geometry and centroid endpoints were unavailable on extraction date.
The documented bbox endpoint retains exact node coordinates and polygon bounds.
Polygon midpoints are used in downstream assignment, with node-only sensitivity.
"""
from pathlib import Path
import geopandas as gpd,requests,json,datetime,hashlib,time,concurrent.futures,argparse
ROOT=Path(__file__).resolve().parents[1];raw=ROOT/'05_Data/raw/osm_2022';raw.mkdir(exist_ok=True)
g=gpd.read_parquet(ROOT/'05_Data/processed/study_counties.parquet').to_crs(4326)
URL='https://api.ohsome.org/v1/elements/bbox'
FILTER='amenity in (cafe,restaurant,fast_food,bar,pub)'
def run(row):
 code=row.GEOID;target=raw/(code+'.geojson')
 if target.exists():
  obj=json.loads(target.read_text(encoding='utf8'))
  if 'features' in obj: print('CACHED',code,len(obj['features']),flush=True);return True
 # Expand by 0.02 degrees to support boundary and nearby-place checks.
 a,b,c,d=row.geometry.bounds
 params={'bboxes':f'{a-.02:.6f},{b-.02:.6f},{c+.02:.6f},{d+.02:.6f}','filter':FILTER,'time':'2022-12-31T23:59:59Z','properties':'tags','timeout':300}
 (raw/(code+'.query.json')).write_text(json.dumps({'url':URL,'params':params},indent=2))
 t=time.time()
 try:
  r=requests.get(URL,params=params,headers={'User-Agent':'CafeHealthOpenDataResearch/1.0'},timeout=(30,340));r.raise_for_status();obj=r.json()
  if 'features' not in obj:raise RuntimeError(str(obj)[:300])
  target.write_bytes(r.content)
  meta={'countyfips':code,'county':row.NAME,'url':r.url,'params':params,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':round(time.time()-t,1),'features':len(obj['features']),'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest(),'attribution':obj.get('attribution'),'apiVersion':obj.get('apiVersion')}
  (raw/(code+'.source.json')).write_text(json.dumps(meta,indent=2),encoding='utf8')
  print('OK',code,row.NAME,len(obj['features']),round(time.time()-t),flush=True);return True
 except Exception as e:
  (raw/(code+'.error.json')).write_text(json.dumps({'error':str(e),'time':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2))
  print('ERROR',code,str(e)[:200],flush=True);return False
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int);args=parser.parse_args()
 items=list(g.itertuples())
 if args.limit:items=items[:args.limit]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(run,items))
 print('COMPLETE',sum(results),'/',len(results),flush=True)
 if not all(results):raise SystemExit(2)
