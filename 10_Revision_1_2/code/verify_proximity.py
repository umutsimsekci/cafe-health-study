"""Independently check centroid proximity counts and projection sensitivity."""
from pathlib import Path
import sys, json, hashlib
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
HERE=BASE.parent/'results'
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from pyproj import Transformer, Geod

SOURCE=ROOT/'05_Data'

def main():
 global SOURCE,HERE
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=SOURCE);ap.add_argument('--output',type=Path,default=HERE)
 args=ap.parse_args();SOURCE=args.source;HERE=args.output;HERE.mkdir(parents=True,exist_ok=True)
 d=pd.read_csv(SOURCE/'processed/analysis_dataset.csv',dtype={'GEOID':str,'countyfips':str})
 p=pd.read_parquet(SOURCE/'processed/osm_features_assigned.parquet')
 p=p[(~p.duplicate_representation)&p.amenity.eq('cafe')].reset_index(drop=True)
 target=pd.read_csv(HERE/'nearby_cafe_exposure.csv',dtype={'GEOID':str,'countyfips':str})
 assert target.GEOID.equals(d.GEOID)
 trans=Transformer.from_crs(4326,5070,always_xy=True)
 back=Transformer.from_crs(5070,4326,always_xy=True)
 px,py=trans.transform(p.longitude.to_numpy(),p.latitude.to_numpy())
 xy=d[['x_m','y_m']].to_numpy()
 brute={r:np.zeros(len(d),dtype=int) for r in [500,1000]}
 # Full all-pairs enumeration avoids the original KD-tree implementation.
 for start in range(0,len(d),128):
  block=xy[start:start+128]
  squared=(block[:,0,None]-px[None,:])**2+(block[:,1,None]-py[None,:])**2
  for r in [500,1000]:brute[r][start:start+len(block)]=(squared<=r*r).sum(axis=1)
 for r in [500,1000]:np.testing.assert_array_equal(brute[r],target[f'mapped_cafes_within_{r}m'])
 lon,lat=back.transform(xy[:,0],xy[:,1])
 def sphere(lon,lat):
  lon=np.deg2rad(lon);lat=np.deg2rad(lat)
  return np.c_[np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)]
 # Search on unit-sphere chord distance, then compute exact WGS84 geodesics.
 # The1.3km candidate radius exceeds both thresholds and measured distortion.
 unit=sphere(p.longitude.to_numpy(),p.latitude.to_numpy());centunit=sphere(lon,lat)
 candidates=cKDTree(unit).query_ball_point(centunit,2*np.sin(1300/(2*6371008.8)))
 geod=Geod(ellps='WGS84');rows=[];max_relative=0.;max_absolute_1km=0.;total_pairs=0
 geocount={r:np.zeros(len(d),dtype=int) for r in [500,1000]}
 for i,idx in enumerate(candidates):
  if not idx:continue
  idx=np.array(idx,dtype=int)
  _,_,dist=geod.inv(np.full(len(idx),lon[i]),np.full(len(idx),lat[i]),p.longitude.to_numpy()[idx],p.latitude.to_numpy()[idx])
  planar=np.hypot(px[idx]-xy[i,0],py[idx]-xy[i,1])
  for r in [500,1000]:geocount[r][i]=int((dist<=r).sum())
  nonzero=dist>1e-4
  if nonzero.any():max_relative=max(max_relative,float(np.abs(planar[nonzero]/dist[nonzero]-1).max()))
  near=dist<=1100
  if near.any():max_absolute_1km=max(max_absolute_1km,float(np.abs(planar[near]-dist[near]).max()))
  total_pairs+=len(idx)
 # Check that no projected-threshold cafe is outside the independent1.3km
 # candidate query. Distance distortion must stay within3percent here.
 assert max_relative<.03
 for r in [500,1000]:
  zero=d.cafe_count.eq(0).to_numpy();projected=brute[r]>0;geo=geocount[r]>0
  rows.append({'radius_m':r,'zero_own_tracts':int(zero.sum()),
               'projected_zero_tracts_with_nearby':int((zero&projected).sum()),
               'geodesic_zero_tracts_with_nearby':int((zero&geo).sum()),
               'geodesic_percent_zero_tracts_with_nearby':float(100*(zero&geo).sum()/zero.sum()),
               'all_tract_count_disagreements_projection_vs_geodesic':int((brute[r]!=geocount[r]).sum()),
               'all_tract_any_nearby_classification_disagreements':int((projected!=geo).sum()),
               'zero_tract_any_nearby_classification_disagreements':int((zero&(projected!=geo)).sum())})
 verification={'all_pairs_projected_count_exact_match':True,
               'geodesic_candidate_radius_m':1300,'geodesic_candidate_pairs':total_pairs,
               'max_relative_projection_distance_difference':max_relative,
               'max_absolute_projection_distance_difference_m_for_geodesic_pairs_within1100m':max_absolute_1km,
               'radii_sensitivity':rows,
               'interpretation':'Main500m/1kmcounts are EPSG5070 planar geometric-centroid counts. WGS84 geodesic counts test threshold sensitivity; neither metric estimates walking access or cafe use.'}
 # Stronger independent extraction coverage check with WGS84 forward circles.
 coverage=[];minimum_margin_deg=np.inf
 for county,idx in d.groupby('countyfips').groups.items():
  box=np.array(json.loads((SOURCE/'raw/osm_2022'/f'{county}.query.json').read_text())['params']['bboxes'].split(','),dtype=float)
  az=np.arange(0,360,5)
  lo,la,_=geod.fwd(np.repeat(lon[idx],len(az)),np.repeat(lat[idx],len(az)),np.tile(az,len(idx)),np.full(len(idx)*len(az),1035.))
  lo=lo.reshape(len(idx),-1);la=la.reshape(len(idx),-1)
  margins=np.c_[lo.min(axis=1)-box[0],la.min(axis=1)-box[1],box[2]-lo.max(axis=1),box[3]-la.max(axis=1)]
  minimum_margin_deg=min(minimum_margin_deg,float(margins.min()))
  assert (margins>0).all()
 verification['independent1035m_geodesic_query_coverage_all_tracts']=True
 verification['minimum1035m_geodesic_circle_rectangle_margin_degrees']=minimum_margin_deg
 # A conservative longitude/latitude rectangle provides a second check that
 # does not depend on angular sampling.110,000m/degree is a lower bound for
 # meridional and cosine-scaled longitudinal distance at the study latitudes.
 conservative_margin=np.inf
 assert lat.min()>25 and lat.max()<48
 for county,idx in d.groupby('countyfips').groups.items():
  box=np.array(json.loads((SOURCE/'raw/osm_2022'/f'{county}.query.json').read_text())['params']['bboxes'].split(','),dtype=float)
  delta_lat=1035/110000
  delta_lon=1035/(110000*np.cos(np.deg2rad(np.abs(lat[idx])+delta_lat)))
  margins=np.c_[lon[idx]-delta_lon-box[0],lat[idx]-delta_lat-box[1],box[2]-lon[idx]-delta_lon,box[3]-lat[idx]-delta_lat]
  assert (margins>0).all()
  conservative_margin=min(conservative_margin,float(margins.min()))
 verification['independent_conservative1035m_geographic_envelope_coverage_all_tracts']=True
 verification['minimum_conservative_envelope_rectangle_margin_degrees']=conservative_margin
 # Origin of cafes actually used by each analytic centroid circle.
 cafefips=p.GEOID.fillna('').str[:5]
 analytic_geo=set(d.GEOID); selected=set(d.countyfips)
 originalall=pd.read_csv(SOURCE/'processed/all_tracts_and_exclusions.csv',dtype={'GEOID':str,'countyfips':str})
 selected_geoid=set(originalall.GEOID)
 roles=np.select([p.GEOID.isin(analytic_geo),p.GEOID.isin(selected_geoid),p.GEOID.notna()],
                 ['analytic_tract','selected_excluded_tract','assigned_selected_tract_other'],default='outside_selected_tracts')
 links=cKDTree(np.c_[px,py]).query_ball_point(xy,1000)
 used=np.unique(np.concatenate([np.array(v,dtype=int) for v in links if v]))
 rolecounts=pd.Series(roles[used]).value_counts().to_dict()
 totalroles=pd.Series(roles).value_counts().to_dict()
 verification['unique_cafe_records_used_in_any1km_circle']=int(len(used))
 verification['used1km_cafe_record_origin_counts']={k:int(v) for k,v in rolecounts.items()}
 verification['all_retained_cafe_record_origin_counts']={k:int(v) for k,v in totalroles.items()}
 verification['selected_frame_tracts']=len(originalall)
 pd.DataFrame(rows).to_csv(HERE/'proximity_geodesic_sensitivity.csv',index=False)
 geoval=d[['GEOID','countyfips']].copy()
 for r in [500,1000]:geoval[f'mapped_cafes_geodesic_{r}m']=geocount[r]
 geoval.to_csv(HERE/'geodesic_proximity_tract_values.csv',index=False)
 (HERE/'proximity_independent_verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(verification,indent=2),flush=True)

if __name__=='__main__':main()
