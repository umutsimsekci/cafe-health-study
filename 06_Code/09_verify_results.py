"""Independent recomputation of consequential reported numerical results."""
from pathlib import Path
import json
import numpy as np,pandas as pd,geopandas as gpd
from scipy.stats import t
ROOT=Path(__file__).resolve().parents[1];proc=ROOT/'05_Data/processed';tab=ROOT/'03_Tables';val=ROOT/'08_Validation'
d=pd.read_csv(proc/'analysis_dataset.csv',dtype={'GEOID':str,'countyfips':str})
assert d.GEOID.is_unique and len(d)==23527 and d.countyfips.nunique()==50
assert np.allclose(d.cafe_per_10k,d.cafe_count/d.E_TOTPOP*10000)
assert (d.cafe_count>=0).all() and (d.cafe_count%1==0).all()
assert (d.E_TOTPOP>=500).all() and (d.land_km2>0).all()
cols=['cafe_log','log_pop_density','EP_POV150','EP_UNEMP','EP_NOHSDP','EP_AGE65','EP_AGE17','EP_MINRTY','EP_NOVEH']
within=d[cols]-d.groupby('countyfips')[cols].transform('mean');A=within.to_numpy()
y=(d.MHLTH_CrudePrev-d.groupby('countyfips').MHLTH_CrudePrev.transform('mean')).to_numpy()
cross=A.T@A;inv=np.linalg.inv(cross);beta=inv@(A.T@y);resid=y-A@beta
scores=pd.DataFrame(A*resid[:,None],columns=cols).groupby(d.countyfips).sum().to_numpy()
n=len(d);G=d.countyfips.nunique();k=G+len(cols)
cov=inv@(scores.T@scores)@inv*(G/(G-1))*((n-1)/(n-k));se=np.sqrt(cov[0,0]);p=2*t.sf(abs(beta[0]/se),G-1)
r=pd.read_csv(tab/'Table_2_all_outcome_models.csv');primary=r[(r.outcome=='MHLTH')&(r.model=='extended')].iloc[0]
assert np.isclose(beta[0],primary.beta_pp,atol=1e-9)
assert np.isclose(se,primary.se,atol=1e-9)
assert np.isclose(p,primary.p,atol=1e-10)
lo=beta[0]-t.ppf(.975,G-1)*se;hi=beta[0]+t.ppf(.975,G-1)*se
assert np.allclose([lo,hi],[primary.ci_lower,primary.ci_upper],atol=1e-9)
for model in r.model.unique():
 q=r[(r.model==model)&(r.outcome!='MHLTH')];ps=q.p.to_numpy();order=np.argsort(ps);sortedq=ps[order]*len(ps)/np.arange(1,len(ps)+1);sortedq=np.minimum.accumulate(sortedq[::-1])[::-1].clip(0,1);out=np.empty(len(ps));out[order]=sortedq
 assert np.allclose(out,q.q_BH_secondary,atol=1e-10)
# Independently recount mapped features from object-level assignment records.
f=pd.read_parquet(proc/'osm_features_assigned.parquet');kept=f[(f.amenity=='cafe')&(~f.duplicate_representation)]
counts=kept.groupby('GEOID').size();assert np.array_equal(d.GEOID.map(counts).fillna(0).to_numpy(),d.cafe_count.to_numpy())
nodes=kept[(kept.osm_type=='node')&kept.GEOID.isin(d.GEOID)].sample(n=min(500,len(kept)),random_state=20260915)
points=gpd.GeoDataFrame(nodes[['osm_id','GEOID']],geometry=gpd.points_from_xy(nodes.longitude,nodes.latitude),crs=4326)
full=gpd.read_parquet(proc/'study_tracts_full_resolution.parquet').to_crs(4326)
fresh=gpd.sjoin(points.rename(columns={'GEOID':'assigned_geoid'}),full[['GEOID','geometry']],predicate='intersects').sort_values(['osm_id','GEOID']).drop_duplicates('osm_id')
assert len(fresh)==len(nodes) and (fresh.assigned_geoid==fresh.GEOID).all()
report={'status':'Passed within tested scope','sample':{'tracts':n,'counties':G,'unique_geoids':True},'independent_primary_recalculation':{'beta_pp':float(beta[0]),'cluster_se':float(se),'ci_lower':float(lo),'ci_upper':float(hi),'p':float(p),'finite_cluster_df':int(G-1),'full_model_parameters':k},'checks':['Exact density recomputation for every analytical tract','Cafe counts independently regrouped from object-level assignment','Within-county normal equations and manual county-cluster sandwich reproduce primary model coefficient, SE, CI and p','BH secondary q values manually recalculated for every model','500 sampled cafe-node assignments recomputed against full-resolution TIGER/Line polygons'],'limits':['Geographical recomputation is a sample, not an external establishment-validation survey','This check does not validate the original CDC health-estimation model or unknown joint error covariance','Visual rendering and manuscript claim checks are separate required steps']}
(val/'independent_numeric_verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
