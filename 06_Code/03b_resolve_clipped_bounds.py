"""Requery only objects touching extraction edges with clipping disabled."""
from pathlib import Path
import json,requests,numpy as np,hashlib,datetime,concurrent.futures
ROOT=Path(__file__).resolve().parents[1];raw=ROOT/'05_Data/raw/osm_2022';repair=ROOT/'05_Data/raw/osm_bounds_repair';repair.mkdir(exist_ok=True)
targets={}
for p in sorted(raw.glob('*.geojson')):
 query=json.loads(p.with_suffix('.query.json').read_text());bbox=np.array([float(x) for x in query['params']['bboxes'].split(',')])
 for f in json.loads(p.read_text(encoding='utf8'))['features']:
  oid=f['properties']['@osmId']
  if oid.startswith('node/'):continue
  xy=np.asarray(f['geometry']['coordinates'][0]);b=np.r_[xy.min(axis=0),xy.max(axis=0)]
  if np.any(np.isclose(b,bbox,atol=2e-7,rtol=0)):targets[oid]=f
print('CLIPPED BOUND CANDIDATES',len(targets),flush=True)
ids=sorted(targets)
def fetch(oid):
 xy=np.asarray(targets[oid]['geometry']['coordinates'][0]);lo=xy.min(axis=0)-.005;hi=xy.max(axis=0)+.005
 params={'bboxes':','.join(map(str,[*lo,*hi])),'filter':'id:'+oid,'time':'2022-12-31T23:59:59Z','properties':'tags','clipGeometry':'false','timeout':60}
 stem=oid.replace('/','_');p=repair/(stem+'.geojson');q=repair/(stem+'.query.json')
 if p.exists() and q.exists() and json.loads(q.read_text())['params']==params:obj=json.loads(p.read_text(encoding='utf8'))
 else:
  url='https://api.ohsome.org/v1/elements/bbox';q.write_text(json.dumps({'url':url,'params':params},indent=2))
  r=requests.get(url,params=params,timeout=(20,85));r.raise_for_status();obj=r.json();p.write_bytes(r.content)
  p.with_suffix('.source.json').write_text(json.dumps({'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(r.content).hexdigest(),'bytes':len(r.content)},indent=2))
 assert {f['properties']['@osmId'] for f in obj['features']}=={oid},oid
 print('RESOLVED',oid,flush=True)
 return obj['features'][0]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:collected=list(pool.map(fetch,ids))
(repair/'complete_overrides.geojson').write_text(json.dumps({'type':'FeatureCollection','features':collected}),encoding='utf8')
print('REPAIR COMPLETE',len(collected),flush=True)
