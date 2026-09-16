"""Merge source features, audit duplicate representations, assign to tracts."""
from pathlib import Path
import json,unicodedata,re
import numpy as np,pandas as pd,geopandas as gpd
from scipy.spatial import cKDTree
from shapely.geometry import box
ROOT=Path(__file__).resolve().parents[1];proc=ROOT/'05_Data/processed';raw=ROOT/'05_Data/raw/osm_2022'
counties=pd.read_csv(proc/'selected_counties.csv',dtype={'STCNTY':str}); records={};response_n=0
repair=ROOT/'05_Data/raw/osm_bounds_repair/complete_overrides.geojson'
if not repair.exists():raise RuntimeError('Run 03b_resolve_clipped_bounds.py after complete extraction first.')
overrides={f['properties']['@osmId']:f for f in json.loads(repair.read_text(encoding='utf8'))['features']}
for code in counties.STCNTY:
 p=raw/(code+'.geojson')
 if not p.exists():raise RuntimeError('Incomplete OSM retrieval: '+code)
 obj=json.loads(p.read_text(encoding='utf8'));assert obj['type']=='FeatureCollection'
 for f in obj['features']:
  f=overrides.get(f['properties']['@osmId'],f)
  response_n+=1;props=f['properties'];oid=props['@osmId']
  assert props['@snapshotTimestamp']=='2022-12-31T23:59:59Z'
  xy=np.asarray(f['geometry']['coordinates'][0]);lo=xy.min(axis=0);hi=xy.max(axis=0)
  row={'osm_id':oid,'osm_type':oid.split('/')[0],'amenity':props.get('amenity'),'name':props.get('name',''),'brand':props.get('brand',''),'cuisine':props.get('cuisine',''),'longitude':float((lo[0]+hi[0])/2),'latitude':float((lo[1]+hi[1])/2),'bbox_width_deg':float(hi[0]-lo[0]),'bbox_height_deg':float(hi[1]-lo[1]),'snapshot':'2022-12-31T23:59:59Z'}
  if oid in records:assert records[oid]==row,'Conflicting same-date OSM object '+oid
  records[oid]=row
p=pd.DataFrame(records.values()).sort_values('osm_id').reset_index(drop=True)
def norm(s):return re.sub(r'[^\w]','',unicodedata.normalize('NFKD',s).casefold())
p['normalized_name']=p.name.map(norm)
pg=gpd.GeoDataFrame(p,geometry=gpd.points_from_xy(p.longitude,p.latitude),crs=4326)
metric=pg.to_crs(5070);coords=np.c_[metric.geometry.x,metric.geometry.y]
tree=cKDTree(coords);pairs=tree.query_pairs(25,output_type='ndarray');drops=set();dups=[]
priority={'node':0,'way':1,'relation':2}
for i,j in pairs:
 a=p.iloc[i];b=p.iloc[j]
 if a.amenity==b.amenity and a.normalized_name and a.normalized_name==b.normalized_name and a.osm_type!=b.osm_type:
  keep,drop=(i,j) if priority[a.osm_type]<=priority[b.osm_type] else (j,i)
  drops.add(drop);dups.append({'kept_id':p.iloc[keep].osm_id,'dropped_id':p.iloc[drop].osm_id,'name':a['name'],'distance_m':float(np.linalg.norm(coords[i]-coords[j])),'rule':'same normalized nonempty name and category; different OSM types within 25 m'})
p['duplicate_representation']=p.index.isin(drops)
g=gpd.read_parquet(proc/'health_geography.parquet')
full=gpd.read_parquet(proc/'study_tracts_full_resolution.parquet').to_crs(g.crs)
assert set(g.GEOID)==set(full.GEOID)
fullgeom=full.set_index('GEOID').geometry
g['geometry']=g.GEOID.map(fullgeom)
# Refresh centroids using full-resolution land/water tract geometry.
cent=g.to_crs(5070).geometry.centroid;g['x_m']=cent.x;g['y_m']=cent.y
ll=gpd.GeoSeries(cent,crs=5070).to_crs(4326);g['longitude']=ll.x;g['latitude']=ll.y
# Bbox midpoint ambiguity is assessed separately from unmatched outer boundaries.
nonnode=p.osm_type!='node'
bb=gpd.GeoDataFrame(p.loc[nonnode,['osm_id']],geometry=[box(row.longitude-row.bbox_width_deg/2,row.latitude-row.bbox_height_deg/2,row.longitude+row.bbox_width_deg/2,row.latitude+row.bbox_height_deg/2) for row in p.loc[nonnode].itertuples()],crs=4326)
bbj=gpd.sjoin(bb,g[['GEOID','geometry']].to_crs(4326),how='left',predicate='intersects')
hits=bbj.groupby('osm_id').GEOID.nunique()
p['bbox_multiple_tracts']=p.osm_id.map(hits).fillna(0)>1
p['bbox_diagonal_m']=np.hypot(p.bbox_width_deg*111320*np.cos(np.deg2rad(p.latitude)),p.bbox_height_deg*111320)
p['bbox_location_ambiguous']=nonnode&(p.bbox_multiple_tracts|(p.bbox_diagonal_m>200))
assign=gpd.sjoin(pg,g[['GEOID','geometry']].to_crs(4326),how='left',predicate='intersects')
boundary_multiple=int(assign.osm_id.duplicated().sum())
assign=assign.sort_values(['osm_id','GEOID']).drop_duplicates('osm_id')
assign=assign.set_index('osm_id').reindex(p.osm_id).reset_index()
p['GEOID']=assign.GEOID.values
unassigned=p.GEOID.isna();nearest_ids=pd.Series(index=p.index,dtype='object');near_dist=pd.Series(index=p.index,dtype='float')
if unassigned.any():
 near=gpd.sjoin_nearest(metric.loc[unassigned],g[['GEOID','geometry']].to_crs(5070),how='left',max_distance=100,distance_col='distance_m')
 near=near.sort_values(['osm_id','distance_m','GEOID']).drop_duplicates('osm_id').set_index('osm_id')
 nearest_ids.loc[unassigned]=p.loc[unassigned,'osm_id'].map(near.GEOID).values
 near_dist.loc[unassigned]=p.loc[unassigned,'osm_id'].map(near.distance_m).values
p['nearest_tract_within_100m']=nearest_ids;p['boundary_distance_m']=near_dist
p.to_parquet(proc/'osm_features_assigned.parquet',index=False)
pd.DataFrame(dups).to_csv(ROOT/'08_Validation/osm_duplicate_candidates.csv',index=False)
kept=p[~p.duplicate_representation]
for category in ['cafe','restaurant','fast_food','bar','pub']:
 counts=kept[kept.amenity==category].groupby('GEOID').size()
 g[category+'_count']=g.GEOID.map(counts).fillna(0).astype(int)
cafes=kept[kept.amenity=='cafe']
g['cafe_node_count']=g.GEOID.map(cafes[cafes.osm_type=='node'].groupby('GEOID').size()).fillna(0).astype(int)
g['cafe_unmerged_count']=g.GEOID.map(p[p.amenity=='cafe'].groupby('GEOID').size()).fillna(0).astype(int)
g['cafe_unambiguous_count']=g.GEOID.map(cafes[~cafes.bbox_location_ambiguous].groupby('GEOID').size()).fillna(0).astype(int)
g['cafe_100m_count']=g.cafe_count+g.GEOID.map(cafes[cafes.GEOID.isna()].groupby('nearest_tract_within_100m').size()).fillna(0).astype(int)
g['noncafe_count']=g[['restaurant_count','fast_food_count','bar_count','pub_count']].sum(axis=1)
for k,count,denom in [('cafe_per_10k','cafe_count','E_TOTPOP'),('cafe_node_per_10k','cafe_node_count','E_TOTPOP'),('cafe_unmerged_per_10k','cafe_unmerged_count','E_TOTPOP'),('cafe_100m_per_10k','cafe_100m_count','E_TOTPOP'),('noncafe_per_10k','noncafe_count','E_TOTPOP')]:g[k]=g[count]/g[denom]*10000
g['cafe_per_km2']=g.cafe_count/g.land_km2
g['cafe_unambiguous_per_10k']=g.cafe_unambiguous_count/g.E_TOTPOP*10000
g['cafe_present']=(g.cafe_count>0).astype(int)
g['cafe_log']=np.log2(1+g.cafe_per_10k)
g['log_pop_density']=np.log2(g.pop_density.where(g.pop_density>0))
g['noncafe_log']=np.log2(1+g.noncafe_per_10k)
g.to_parquet(proc/'all_tracts_with_exposures.parquet',index=False)
cov=['log_pop_density','EP_POV150','EP_UNEMP','EP_NOHSDP','EP_AGE65','EP_AGE17','EP_MINRTY','EP_NOVEH']
g['exclude_small_population']=g.E_TOTPOP<500;g['exclude_land']=g.land_km2<=0
g['exclude_missing_covariates']=g[cov].isna().any(axis=1)
g['exclude_missing_primary']=g.MHLTH_CrudePrev.isna()
g['included']=~g[['exclude_small_population','exclude_land','exclude_missing_covariates','exclude_missing_primary']].any(axis=1)
d=g[g.included].copy().reset_index(drop=True);d.to_parquet(proc/'analysis_dataset.parquet',index=False)
d.drop(columns='geometry').to_csv(proc/'analysis_dataset.csv',index=False)
g.drop(columns='geometry').to_csv(proc/'all_tracts_and_exclusions.csv',index=False)
flow=[];m=pd.Series(True,index=g.index)
for label,col in [('Resident population below 500','exclude_small_population'),('Nonpositive land area','exclude_land'),('Missing model covariates','exclude_missing_covariates'),('Missing primary health estimate','exclude_missing_primary')]:
 removed=int((m&g[col]).sum());m&=~g[col];flow.append({'reason':label,'excluded_sequentially':removed,'remaining':int(m.sum())})
audit={'raw_feature_records_across_queries':response_n,'unique_osm_features_in_expanded_bboxes':len(p),'cross_type_duplicates_removed':len(drops),'multiple_tract_boundary_assignments_resolved_by_geoid':boundary_multiple,'mapped_cafes_in_selected_counties_before_eligibility':int(g.cafe_count.sum()),'cafes_outside_tract_geometry_but_within_100m':int(cafes.nearest_tract_within_100m.notna().sum()),'cafes_in_analysis':int(d.cafe_count.sum()),'analysis_tracts':len(d),'analysis_counties':d.countyfips.nunique(),'analysis_resident_population':int(d.E_TOTPOP.sum()),'tracts_with_no_mapped_cafe':int((d.cafe_count==0).sum()),'sample_flow':flow,'unique_analysis_geoid':bool(d.GEOID.is_unique),'exposure_quantiles':d.cafe_per_10k.quantile([0,.25,.5,.75,.9,.99,1]).to_dict()}
audit['nonnode_cafes_with_ambiguous_bbox_location']=int(((p.amenity=='cafe')&p.bbox_location_ambiguous).sum())
audit['extraction_edge_objects_requeried_unclipped']=len(overrides)
audit['ambiguous_bbox_definition']='Non-node bbox intersects multiple study tracts or approximate diagonal exceeds 200 m; excluding these is a location sensitivity.'
(ROOT/'08_Validation/exposure_and_sample_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf8')
print(json.dumps(audit,indent=2),flush=True)
