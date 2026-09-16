"""Build a fully local, standalone interactive geographic supplement."""
from pathlib import Path
import json,requests,geopandas as gpd
ROOT=Path(__file__).resolve().parents[1];proc=ROOT/'05_Data/processed';out=ROOT/'04_Interactive_Map'
out.mkdir(parents=True, exist_ok=True)
d=gpd.read_parquet(proc/'analysis_with_predictions.parquet')
g=gpd.read_parquet(proc/'study_tracts.parquet')[['GEOID','geometry']].merge(d.drop(columns='geometry'),on='GEOID',validate='one_to_one')
cols=['GEOID','countyfips','CountyName','StateAbbr','E_TOTPOP','cafe_count','cafe_per_10k','cafe_per_km2','MHLTH_CrudePrev','MHLTH_lower','MHLTH_upper','OBESITY_CrudePrev','OBESITY_lower','OBESITY_upper','LPA_CrudePrev','LPA_lower','LPA_upper','EP_POV150','geometry']
g=g[cols].to_crs(5070);g.geometry=g.geometry.simplify(80,preserve_topology=True);g=g.to_crs(4326)
obj=json.loads(g.to_json(drop_id=True));
for f in obj['features']:
 for k,v in f['properties'].items():
  if isinstance(v,float):f['properties'][k]=round(v,3)
data=json.dumps(obj,separators=(',',':'),ensure_ascii=False).replace('</','<\\/')
deps=ROOT/'06_Code/vendor';deps.mkdir(exist_ok=True);js=deps/'d3.v7.9.0.min.js'
if not js.exists():
 r=requests.get('https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js',timeout=40);r.raise_for_status();js.write_bytes(r.content)
license_path=deps/'D3_LICENSE.txt'
if not license_path.exists():
 r=requests.get('https://cdn.jsdelivr.net/npm/d3@7.9.0/LICENSE',timeout=40);r.raise_for_status();license_path.write_bytes(r.content)
template=(Path(__file__).parent/'map_template.html').read_text(encoding='utf8')
html=template.replace('__D3__','/* '+license_path.read_text(encoding='utf8')+' */\n'+js.read_text(encoding='utf8')).replace('__GEOJSON__',data)
(out/'Cafe_Health_Interactive_Map.html').write_text(html,encoding='utf8')
(out/'README.txt').write_text('Open Cafe_Health_Interactive_Map.html in a modern browser. All data and D3 are embedded; no internet connection or remote map tiles are needed. This is the interactive supplement to the manuscript. Source details are inside the map. Geometry is simplified for display only. Original analytical data and full-resolution geometry are in 05_Data.\n',encoding='utf8')
print('MAP COMPLETE',len(obj['features']),'tracts',len(html),'characters')
