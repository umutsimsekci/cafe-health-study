"""Exploratory record-concordance audit, not a business census or field validation.
Rules are fixed before first concordance results and do not use health outcomes.
"""
from pathlib import Path
import json,re,unicodedata,datetime,difflib
import numpy as np,pandas as pd,geopandas as gpd
from scipy.spatial import cKDTree
BASE=Path(__file__).resolve().parent;SRC=BASE.parent/'sources'
ROOT=BASE.parents[1];DEST=BASE.parent/'results';DEST.mkdir(exist_ok=True)
plan={
 'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'Exploratory, outcome-blind record-linkage rules before first concordance results',
 'area':'Official Chicago city boundary from public portal, retrieved2026; not represented as a historical boundary',
 'external_eligibility':'Retail Food Establishment term spanning31Dec2022, issued by that date; AAI or cancellation/revocation later than31Dec2022. Exclude cancelled/revoked by date and missing/ambiguous status. Deduplicate license_number+address, retaining latest issued eligible term.',
 'matching':'All nonduplicate OSM hospitality objects inside Chicago boundary. Name normalization unicode ASCII lowercase, alphanumerics, remove LLC/INC/CORP/LTD/CO/COMPANY and numeric store identifiers. Identity score maximum exact-or-SequenceMatcher across name/brand and DBA. Also accept identical explicitly named Starbucks/Dunkin/Peets/Caribou/Philz/Intelligentsia/Colectivo/Dollop brands. Require score>=0.88 and <=100m. Rank candidate links descending identity score then ascending distance; greedy one-to-one. Record candidate ambiguity and all candidates. Report25/50/100m distance sensitivity.',
 'reverse_subset':'Licensed names containing whole word COFFEE or STARBUCKS; an explicitly coffee-named proxy subset, not a complete cafe inventory. Additional broad name subset CAFE/COFFEE/STARBUCKS for sensitivity, not cafe classification ground truth.',
 'inspection_support':'Link eligible license number to any2022 inspection; separately identify non-license inspections with Pass, Pass w/Conditions or Fail. Out of Business/Not Ready/No Entry are not operational confirmation.',
 'SES':'All eligible study tracts with centroid within city; quartiles of EP_POV150. Show concordance within strata; unmatched and out-of-sample addresses retained. No health outcomes used in matching.',
 'limits':'Administrative records are retrospectively updated; license does not prove actual operation, social availability or correct amenity classification. Name-based linkage and geocoding can fail; no national completeness/sensitivity/PPV claims.'
}
pp=BASE.parent/'methods/chicago_audit_plan.json'
if not pp.exists():pp.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
cut=pd.Timestamp('2022-12-31T23:59:59')
lic=pd.read_json(SRC/'chicago_licenses_spanning_2022end.json',dtype={'license_number':str,'id':str})
assert len(lic)==int(json.loads((SRC/'chicago_licenses_count.json').read_text())[0]['n'])
assert lic.id.is_unique
for col in ['date_issued','license_start_date','expiration_date','license_status_change_date']:lic[col]=pd.to_datetime(lic[col],errors='coerce')
lic['temporal_eligible']=(lic.date_issued<=cut)&(lic.license_start_date<=cut)&(lic.expiration_date>=cut.normalize())&((lic.license_status=='AAI')|(lic.license_status.isin(['AAC','REV','REA'])&(lic.license_status_change_date>cut)))
lic['temporal_reason']=np.select([lic.date_issued.isna(),lic.date_issued>cut,lic.license_status.isin(['AAC','REV'])&(lic.license_status_change_date<=cut),lic.temporal_eligible],['missing issue date','issued after reference date','cancelled/revoked by reference date','eligible'],default='unresolved temporal status')
lic.to_csv(DEST/'chicago_license_temporal_screen.csv',index=False)
eligible=lic[lic.temporal_eligible].sort_values(['date_issued','license_id']).drop_duplicates(['license_number','address'],keep='last').copy()
boundary=gpd.read_file(SRC/'chicago_city_boundary.geojson').to_crs(4326).geometry.union_all()
def in_city(df):
    g=gpd.GeoDataFrame(df.copy(),geometry=gpd.points_from_xy(pd.to_numeric(df.longitude,errors='coerce'),pd.to_numeric(df.latitude,errors='coerce')),crs=4326)
    return g[g.geometry.notna()&g.geometry.intersects(boundary)].copy()
active=in_city(eligible).reset_index(drop=True)
osm=pd.read_parquet(ROOT/'05_Data/processed/osm_features_assigned.parquet')
osm=in_city(osm[~osm.duplicate_representation]).reset_index(drop=True)
d=gpd.read_parquet(ROOT/'05_Data/processed/analysis_dataset.parquet')
city_centroids=gpd.GeoSeries(d.to_crs(5070).geometry.centroid,crs=5070).to_crs(4326)
citytract=d[city_centroids.intersects(boundary)].copy()
# Do not treat centroid-selected tracts as a sum of Chicago population.
citytract['poverty_quartile']=pd.qcut(citytract.EP_POV150,4,labels=['Q1 lowest','Q2','Q3','Q4 highest'])
poverty=citytract.set_index('GEOID').poverty_quartile.astype(str).to_dict()
osm['poverty_quartile']=osm.GEOID.map(poverty).fillna('Outside eligible city-centroid tracts')
assigned=gpd.sjoin(active,d[['GEOID','geometry']].to_crs(4326),how='left',predicate='intersects').sort_values(['license_number','GEOID']).drop_duplicates('license_number')
active['GEOID']=active.license_number.map(assigned.set_index('license_number').GEOID)
active['poverty_quartile']=active.GEOID.map(poverty).fillna('Outside eligible city-centroid tracts')
def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    tokens=re.findall('[a-z]+',s)
    return ' '.join(t for t in tokens if t not in {'llc','inc','corp','ltd','co','company'})
chains=['starbucks','dunkin','peets','caribou','philz','intelligentsia','colectivo','dollop']
def chain(s):
    s=s.replace(' ','');return next((c for c in chains if c in s),'')
def score(a,b):
    if not a or not b:return 0.
    if a==b:return 1.
    ca,cb=chain(a),chain(b)
    if ca and ca==cb:return .99
    # Generic labels alone are not sufficient identification.
    if a in {'cafe','coffee','coffee shop','restaurant'} or b in {'cafe','coffee','coffee shop','restaurant'}:return 0.
    return difflib.SequenceMatcher(None,a,b,autojunk=False).ratio()
active['normalized_name']=active.doing_business_as_name.map(norm)
osm['audit_name']=osm['name'].map(norm);osm['audit_brand']=osm.brand.map(norm)
ap=active.to_crs(26916);op=osm.to_crs(26916)
axy=np.c_[ap.geometry.x,ap.geometry.y];oxy=np.c_[op.geometry.x,op.geometry.y]
tree=cKDTree(axy);pairs=[]
for oi,near in enumerate(tree.query_ball_point(oxy,100)):
    for ai in near:
        a=active.iloc[ai];o=osm.iloc[oi];s=max(score(o.audit_name,a.normalized_name),score(o.audit_brand,a.normalized_name))
        pairs.append({'oi':oi,'ai':ai,'osm_id':o.osm_id,'osm_amenity':o.amenity,'osm_name':o['name'],'license_number':a.license_number,'license_name':a.doing_business_as_name,'license_address':a.address,'distance_m':float(np.linalg.norm(oxy[oi]-axy[ai])),'name_score':s})
candidate=pd.DataFrame(pairs).sort_values(['name_score','distance_m','osm_id','license_number'],ascending=[False,True,True,True])
candidate.to_csv(DEST/'chicago_candidate_links.csv',index=False)
def links(maxdist):
    options=candidate[(candidate.name_score>=.88)&(candidate.distance_m<=maxdist)]
    usedo=set();useda=set();keep=[]
    for ix,r in options.iterrows():
        if r.oi in usedo or r.ai in useda:continue
        keep.append(ix);usedo.add(r.oi);useda.add(r.ai)
    return candidate.loc[keep].copy()
matched=links(100);matcho=matched.set_index('osm_id');matcha=matched.set_index('license_number')
osm['linked_license']=osm.osm_id.map(matcho.license_number)
osm['link_distance_m']=osm.osm_id.map(matcho.distance_m)
osm['link_name_score']=osm.osm_id.map(matcho.name_score)
osm['candidate_qualified_n']=osm.osm_id.map(candidate[candidate.name_score>=.88].groupby('osm_id').size()).fillna(0).astype(int)
active['linked_osm_id']=active.license_number.map(matcha.osm_id)
active['linked_osm_amenity']=active.license_number.map(matcha.osm_amenity)
active['coffee_named_subset']=active.doing_business_as_name.str.contains(r'\b(?:COFFEE|STARBUCKS)\b',case=False,na=False)
active['broad_cafe_named_subset']=active.doing_business_as_name.str.contains(r'\b(?:CAFE|COFFEE|STARBUCKS)\b',case=False,na=False)
ins=pd.read_json(SRC/'chicago_2022_inspections.json',dtype={'license_':str})
assert len(ins)==ins.inspection_id.nunique()==sum(int(x['n']) for x in json.loads((SRC/'chicago_2022_types.json').read_text()))
ins['record_date']=pd.to_datetime(ins.inspection_date)
assert (ins.record_date.dt.year==2022).all()
positive=ins[ins.results.isin(['Pass','Pass w/ Conditions','Fail'])&~ins.inspection_type.str.contains('License',case=False,na=False)]
active['any_2022_inspection']=active.license_number.isin(ins.license_)
active['nonlicensing_2022_inspection']=active.license_number.isin(positive.license_)
osm['linked_nonlicensing_2022_inspection']=osm.linked_license.notna()&osm.linked_license.isin(positive.license_.dropna())
matched.to_csv(DEST/'chicago_accepted_links.csv',index=False)
osm.drop(columns='geometry').to_csv(DEST/'chicago_osm_record_audit.csv',index=False)
active.drop(columns='geometry').to_csv(DEST/'chicago_eligible_license_audit.csv',index=False)
summary=[]
for dist in [25,50,100]:
    mm=links(dist);oset=set(mm.osm_id);aset=set(mm.license_number[mm.osm_amenity=='cafe'])
    for label,subset,pred in [('OSM cafe to eligible license',osm[osm.amenity=='cafe'],'osm_id'),('Coffee-named license to OSM cafe',active[active.coffee_named_subset],'license_number'),('Broad cafe-named license to OSM cafe',active[active.broad_cafe_named_subset],'license_number')]:
        ids=oset if pred=='osm_id' else aset
        for group in ['All']+sorted(subset.poverty_quartile.unique()):
            dd=subset if group=='All' else subset[subset.poverty_quartile==group]
            n=len(dd);k=int(dd[pred].isin(ids).sum())
            summary.append({'comparison':label,'maximum_distance_m':dist,'poverty_stratum':group,'denominator':n,'linked_n':k,'concordance_percent':100*k/n if n else None})
pd.DataFrame(summary).to_csv(DEST/'chicago_concordance_summary.csv',index=False)
receipt={'source_license_rows':len(lic),'license_screen':lic.temporal_reason.value_counts().to_dict(),'eligible_deduplicated_license_records':len(eligible),'eligible_geocoded_city_records':len(active),'osm_city_all_hospitality':len(osm),'osm_city_cafes':int((osm.amenity=='cafe').sum()),'inspection_rows':len(ins),'city_centroid_eligible_tracts':len(citytract),'poverty_quartile_edges':citytract.EP_POV150.quantile([0,.25,.5,.75,1]).to_dict(),'matched_osm_cafes':int(osm.loc[osm.amenity=='cafe','linked_license'].notna().sum()),'matched_osm_cafes_with_nonlicensing_inspection':int(osm.loc[osm.amenity=='cafe','linked_nonlicensing_2022_inspection'].sum()),'coffee_subset_alternative_amenity':active.loc[active.coffee_named_subset,'linked_osm_amenity'].fillna('unmatched').value_counts().to_dict(),'health_outcomes_used_in_linkage':False}
(DEST/'chicago_audit_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2));print(pd.DataFrame(summary).query('poverty_stratum == "All"').to_string(index=False))
