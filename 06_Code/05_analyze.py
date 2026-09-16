"""Prespecified ecological models and sensitivity checks, never individual effects.

Intervals condition on PLACES point estimates and omit their unknown joint
estimation covariance. They must not be described as total uncertainty.
"""
from pathlib import Path
import json,os,sys,importlib.metadata,warnings
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import numpy as np,pandas as pd,geopandas as gpd
from scipy import stats,sparse
from scipy.spatial import cKDTree
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.outliers_influence import variance_inflation_factor
ROOT=Path(__file__).resolve().parents[1];proc=ROOT/'05_Data/processed';tab=ROOT/'03_Tables';val=ROOT/'08_Validation'
d=gpd.read_parquet(proc/'analysis_dataset.parquet').reset_index(drop=True)
OUT=['MHLTH','DEPRESSION','GHLTH','PHLTH','OBESITY','LPA','CSMOKING','DIABETES']
LABEL={'MHLTH':'Frequent mental distress','DEPRESSION':'Diagnosed depression','GHLTH':'Fair or poor self-rated health','PHLTH':'Frequent physical distress','OBESITY':'Obesity','LPA':'Physical inactivity','CSMOKING':'Current smoking','DIABETES':'Diagnosed diabetes'}
COV=['log_pop_density','EP_POV150','EP_UNEMP','EP_NOHSDP','EP_AGE65','EP_AGE17','EP_MINRTY','EP_NOVEH']
np.random.seed(20260915)
def design(data,exposure='cafe_log',model='extended',quadratic=False):
 cols=[exposure]
 if model in ['context','extended','hospitality']:cols+=['log_pop_density']
 if model in ['extended','hospitality']:cols+=COV[1:]
 if model=='hospitality':cols+=['noncafe_log']
 X=data[cols].astype(float).copy()
 if quadratic:X['exposure_squared']=data[exposure]**2
 if model!='unadjusted':X=pd.concat([X,pd.get_dummies(data.countyfips,prefix='county',drop_first=True,dtype=float)],axis=1)
 return sm.add_constant(X,has_constant='add')
def fit(data,outcome='MHLTH',exposure='cafe_log',model='extended',weighted=False,quadratic=False):
 X=design(data,exposure,model,quadratic);y=data[outcome+'_CrudePrev'].astype(float)
 m=sm.WLS(y,X,weights=data.TotalPop18plus) if weighted else sm.OLS(y,X)
 res=m.fit(cov_type='cluster',cov_kwds={'groups':data.countyfips,'use_correction':True,'df_correction':True},use_t=True)
 return res,X
def record(res,exposure,data,outcome,model):
 ci=res.conf_int().loc[exposure]
 return {'outcome':outcome,'outcome_label':LABEL[outcome],'model':model,'exposure':exposure,'n':int(res.nobs),'counties':int(data.countyfips.nunique()),'beta_pp':float(res.params[exposure]),'se':float(res.bse[exposure]),'ci_lower':float(ci.iloc[0]),'ci_upper':float(ci.iloc[1]),'p':float(res.pvalues[exposure]),'r_squared':float(res.rsquared),'cluster_reference_df':int(data.countyfips.nunique()-1)}
rows=[];models={}
for outcome in OUT:
 dd=d.dropna(subset=[outcome+'_CrudePrev'])
 for model in ['unadjusted','context','extended','hospitality']:
  r,X=fit(dd,outcome,model=model);rows.append(record(r,'cafe_log',dd,outcome,model))
  if model=='extended':models[outcome]=(r,X)
 print('MODELED',outcome,flush=True)
results=pd.DataFrame(rows);results['q_BH_secondary']=np.nan;results['q_BY_secondary']=np.nan
for model in results.model.unique():
 idx=(results.model==model)&(results.outcome!='MHLTH')
 results.loc[idx,'q_BH_secondary']=multipletests(results.loc[idx,'p'],method='fdr_bh')[1]
 results.loc[idx,'q_BY_secondary']=multipletests(results.loc[idx,'p'],method='fdr_by')[1]
results.to_csv(tab/'Table_2_all_outcome_models.csv',index=False)
r,X=models['MHLTH'];primary=record(r,'cafe_log',d,'MHLTH','extended')
d['primary_fitted']=r.fittedvalues;d['primary_residual']=r.resid
# Covariate coefficients in natural units and per one observed SD, not causal importance.
coeff=[]
for term in ['cafe_log']+COV:
 ci=r.conf_int().loc[term];sd=d[term].std(ddof=1)
 coeff.append({'term':term,'beta_per_unit':r.params[term],'ci_lower':ci.iloc[0],'ci_upper':ci.iloc[1],'sd':sd,'beta_per_sd_pp':r.params[term]*sd,'lower_per_sd_pp':ci.iloc[0]*sd,'upper_per_sd_pp':ci.iloc[1]*sd,'p':r.pvalues[term]})
pd.DataFrame(coeff).to_csv(tab/'Table_S2_covariate_coefficients.csv',index=False)
# Within-county VIF avoids confusing county FE with contextual collinearity.
Z=d[['cafe_log']+COV].astype(float);Z=Z-Z.groupby(d.countyfips).transform('mean')
vifs=[{'term':term,'within_county_VIF':variance_inflation_factor(Z.to_numpy(),i)} for i,term in enumerate(Z.columns)]
pd.DataFrame(vifs).to_csv(val/'covariate_collinearity.csv',index=False)
# Primary-outcome sensitivity analyses; no search for significant subgroups.
sens=[]
for name,exposure,dd,weighted,model in [
 ('Primary model','cafe_log',d,False,'extended'),
 ('Additional noncafe hospitality density','cafe_log',d,False,'hospitality'),
 ('Adult population weighted','cafe_log',d,True,'extended'),
 ('Exclude exposure above 99th percentile','cafe_log',d[d.cafe_per_10k<=d.cafe_per_10k.quantile(.99)],False,'extended'),
 ('Cafe presence versus none','cafe_present',d,False,'extended'),
 ('Per square kilometre','cafe_per_km2',d,False,'extended'),
 ('Node-only mapped cafes','cafe_node_per_10k',d,False,'extended'),
 ('Unmerged OSM representations','cafe_unmerged_per_10k',d,False,'extended'),
 ('Outer-boundary nearest assignment within 100 m','cafe_100m_per_10k',d,False,'extended'),
 ('Exclude ambiguous nonnode bbox locations','cafe_unambiguous_per_10k',d,False,'extended'),
 ]:
  dd=dd.copy()
  if exposure.endswith(('per_km2','per_10k')):dd['alternative_log']=np.log2(1+dd[exposure]);exposure='alternative_log'
  rr,xx=fit(dd,exposure=exposure,model=model,weighted=weighted);z=record(rr,exposure,dd,'MHLTH',name);sens.append(z)
p2025=pd.read_csv(ROOT/'05_Data/raw/places_2025.csv',dtype={'TractFIPS':str})
p2025.TractFIPS=p2025.TractFIPS.str.zfill(11)
assert p2025.TractFIPS.is_unique
lagged=d.copy();lagged['MHLTH_CrudePrev']=lagged.GEOID.map(p2025.set_index('TractFIPS').MHLTH_CrudePrev)
lagged=lagged.dropna(subset=['MHLTH_CrudePrev'])
rr,xx=fit(lagged);sens.append(record(rr,'cafe_log',lagged,'MHLTH','2023 outcome with baseline 2022 exposure'))
pd.DataFrame(sens).to_csv(tab/'Table_3_sensitivity.csv',index=False)
# Quadratic curve is a declared exploratory shape check, with cluster intervals.
qr,qX=fit(d,quadratic=True);grid=np.linspace(0,d.cafe_log.quantile(.99),100)
curve=[];crit=stats.t.ppf(.975,d.countyfips.nunique()-1)
idx=list(qX.columns);i=idx.index('cafe_log');j=idx.index('exposure_squared')
for x in grid:
 contrast=np.zeros(qX.shape[1]);contrast[i]=x;contrast[j]=x*x
 estimate=float(contrast@qr.params);se=float(np.sqrt(max(0,contrast@qr.cov_params()@contrast)))
 curve.append({'cafe_per_10k':2**x-1,'log_exposure':x,'difference_pp_vs_zero':estimate,'ci_lower':estimate-crit*se,'ci_upper':estimate+crit*se})
pd.DataFrame(curve).to_csv(tab/'Figure_4_curve_data.csv',index=False)
# Leave-one-county-out coefficient stability using within-county sufficient statistics.
# These estimates are not independent replications.
A=Z.to_numpy();y=d.MHLTH_CrudePrev-d.groupby('countyfips').MHLTH_CrudePrev.transform('mean')
xtx=A.T@A;xty=A.T@y.to_numpy();loo=[]
for county in sorted(d.countyfips.unique()):
 mask=(d.countyfips==county).to_numpy();b=np.linalg.lstsq(xtx-A[mask].T@A[mask],xty-A[mask].T@y.to_numpy()[mask],rcond=None)[0]
 loo.append({'omitted_countyfips':county,'beta_pp':b[0]})
pd.DataFrame(loo).to_csv(tab/'Table_S3_leave_one_county_out.csv',index=False)
# Spatial diagnostic: symmetric 8-nearest-neighbour graph, capped at 100 km.
coords=d[['x_m','y_m']].to_numpy();tree=cKDTree(coords);dist,nei=tree.query(coords,k=9)
ii=np.repeat(np.arange(len(d)),8);jj=nei[:,1:].ravel();valid=dist[:,1:].ravel()<=100000
W=sparse.csr_matrix((np.ones(valid.sum()),(ii[valid],jj[valid])),shape=(len(d),len(d)));W=W.maximum(W.T);W.setdiag(0);W.eliminate_zeros()
degrees=np.asarray(W.sum(axis=1)).ravel();W=sparse.diags(1/np.maximum(degrees,1))@W;S0=float(W.sum());n=len(d)
def moran(z):
 z=np.asarray(z);z=z-z.mean();return float(n/S0*(z@(W@z))/(z@z))
spatial=[];rng=np.random.default_rng(20260915)
for name,z in [('cafe_log',d.cafe_log),('MHLTH',d.MHLTH_CrudePrev),('primary_residual',r.resid)]:
 observed=moran(z);zz=np.asarray(z)-np.mean(z);perm=np.array([moran(rng.permutation(zz)) for _ in range(999)])
 expected=-1/(n-1);p=(1+np.sum(np.abs(perm-expected)>=abs(observed-expected)))/1000
 spatial.append({'variable':name,'Morans_I':observed,'permutation_p_two_sided':p,'permutations':999,'weight_rule':'symmetric 8NN; 100km cap; row standardized; global permutations'})
pd.DataFrame(spatial).to_csv(tab/'Table_S4_spatial_diagnostics.csv',index=False)
# Conley-style distance-tapered sandwich for the exposure coefficient.
# Conditional on PLACES estimates. No correction for unavailable joint MRP error.
inv=np.linalg.pinv(X.to_numpy().T@X.to_numpy());exposure_index=list(X.columns).index('cafe_log')
influence=r.resid.to_numpy()*(X.to_numpy()@inv[:,exposure_index]);hac=[]
for cutoff in [10000,25000]:
 variance=float(influence@influence);pair_count=0
 for start in range(0,n,500):
  lists=tree.query_ball_point(coords[start:start+500],cutoff)
  for offset,neighbors in enumerate(lists):
   i0=start+offset;js=np.array([j0 for j0 in neighbors if j0>i0],dtype=int)
   if not len(js):continue
   weights=1-np.linalg.norm(coords[js]-coords[i0],axis=1)/cutoff
   variance+=2*influence[i0]*float(weights@influence[js]);pair_count+=len(js)
 se=np.sqrt(variance) if variance>=0 else np.nan
 hac.append({'cutoff_km':cutoff/1000,'beta_pp':r.params.cafe_log,'se':se,'ci_lower':r.params.cafe_log-1.96*se,'ci_upper':r.params.cafe_log+1.96*se,'reference':'normal asymptotic','kernel':'Bartlett distance taper','unique_pairs':pair_count})
 print('SPATIAL HAC',cutoff,flush=True)
pd.DataFrame(hac).to_csv(tab/'Table_S5_spatial_HAC.csv',index=False)
# Descriptive table uses tract medians/IQR, not averages of published CIs.
desc=[]
for label,dd in [('All included tracts',d),('No mapped cafe',d[d.cafe_count==0]),('At least one mapped cafe',d[d.cafe_count>0])]:
 for term in ['E_TOTPOP','cafe_per_10k','cafe_per_km2','pop_density']+COV[1:]+[x+'_CrudePrev' for x in OUT]:
  q=dd[term].quantile([.25,.5,.75]);desc.append({'group':label,'n_tracts':len(dd),'variable':term,'median':q.loc[.5],'q25':q.loc[.25],'q75':q.loc[.75]})
pd.DataFrame(desc).to_csv(tab/'Table_1_descriptive.csv',index=False)
county=d.groupby(['countyfips','CountyName','StateAbbr']).agg(tracts=('GEOID','size'),resident_population=('E_TOTPOP','sum'),cafes=('cafe_count','sum'),zero_cafe_share=('cafe_present',lambda x:1-x.mean()),median_mhlth=('MHLTH_CrudePrev','median')).reset_index()
county['cafes_per_10k']=county.cafes/county.resident_population*10000;county.to_csv(tab/'Table_S1_county_coverage.csv',index=False)
d.to_parquet(proc/'analysis_with_predictions.parquet',index=False)
summary={'primary':primary,'cafe_log_iqr':float(d.cafe_log.quantile(.75)-d.cafe_log.quantile(.25)),'primary_beta_per_iqr_pp':float(r.params.cafe_log*(d.cafe_log.quantile(.75)-d.cafe_log.quantile(.25))),'primary_beta_independent_FWL':float(np.linalg.lstsq(xtx,xty,rcond=None)[0][0]),'primary_model_condition_number':float(r.condition_number),'primary_predicted_range':[float(r.fittedvalues.min()),float(r.fittedvalues.max())],'quadratic_term_p_exploratory':float(qr.pvalues.exposure_squared),'leave_one_county_out_beta_range':[float(pd.DataFrame(loo).beta_pp.min()),float(pd.DataFrame(loo).beta_pp.max())],'spatial':spatial,'spatial_hac':hac,'inference_limitation':'All regression intervals condition on PLACES point estimates and do not propagate their joint model-estimation uncertainty; this covariance is not supplied. Ecological associations cannot identify individual effects.'}
(val/'statistical_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
(ROOT/'06_Code/software_versions.json').write_text(json.dumps({k:importlib.metadata.version(k) for k in ['numpy','pandas','geopandas','scipy','statsmodels','matplotlib','requests','shapely']},indent=2))
assert np.isclose(summary['primary_beta_independent_FWL'],r.params.cafe_log,atol=1e-8)
print(json.dumps(summary,indent=2),flush=True)
