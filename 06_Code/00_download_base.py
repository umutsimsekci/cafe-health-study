"""Acquire authoritative base files. Existing archived inputs are reused."""
from pathlib import Path
import requests,hashlib,json,datetime,concurrent.futures
ROOT=Path(__file__).resolve().parents[1];raw=ROOT/'05_Data/raw';raw.mkdir(parents=True,exist_ok=True)
sources={
 'places_2024.csv':'https://data.cdc.gov/api/views/k9zj-b28y/rows.csv?accessType=DOWNLOAD',
 'places_2025.csv':'https://data.cdc.gov/api/views/yjkw-uj5s/rows.csv?accessType=DOWNLOAD',
 'svi_2022_us.csv':'https://svi.cdc.gov/Documents/Data/2022/csv/states/SVI_2022_US.csv',
 'tracts_2023.zip':'https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_tract_500k.zip',
 'counties_2023.zip':'https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip',
 'svi_2022_documentation.pdf':'https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf',
 'places_2024_metadata.json':'https://data.cdc.gov/api/views/k9zj-b28y.json',
 'places_2025_metadata.json':'https://data.cdc.gov/api/views/yjkw-uj5s.json',
}
def get(item):
 name,url=item;p=raw/name;reused=p.exists()
 if not reused:
  r=requests.get(url,timeout=(25,240));r.raise_for_status();p.write_bytes(r.content)
 b=p.read_bytes();meta=raw/(name+'.source.json')
 if not meta.exists():meta.write_text(json.dumps({'file':name,'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reused_archived_input':reused},indent=2))
 print(name,len(b),flush=True)
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:list(ex.map(get,sources.items()))
