"""Post-results diagnostics, conditional on frozen PLACES point estimates."""
from pathlib import Path
import os,json,hashlib
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import numpy as np,pandas as pd,statsmodels.api as sm
from scipy import stats
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
DEST=BASE.parent/'results';DEST.mkdir(exist_ok=True)
assert (BASE.parent/'methods/analysis_addendum.json').exists()
input_csv=ROOT/'05_Data/processed/analysis_dataset.csv'
if not input_csv.exists():input_csv=input_csv.with_suffix('.csv.gz')
d=pd.read_csv(input_csv,dtype={'GEOID':str,'countyfips':str})
assert len(d)==23527 and d.GEOID.is_unique and d.countyfips.nunique()==50
COV=['log_pop_density','EP_POV150','EP_UNEMP','EP_NOHSDP','EP_AGE65','EP_AGE17','EP_MINRTY','EP_NOVEH']
y=d.MHLTH_CrudePrev.to_numpy();ex=d.cafe_log.to_numpy()
fe=pd.get_dummies(d.countyfips,prefix='county',drop_first=True,dtype=float)
def matrix(kind,flex=False,exposure=None):
    cols=COV+(['noncafe_log'] if kind=='hospitality' else [])
    x=d[cols].astype(float).copy()
    if flex:
        for col in cols:x[col+'_squared']=(d[col]-d[col].mean())**2
    x=pd.concat([x,fe],axis=1)
    if exposure is not None:x['cafe']=exposure
    return sm.add_constant(x,has_constant='add')
def robust(X):
    return sm.OLS(y,X).fit(cov_type='cluster',cov_kwds={'groups':d.countyfips,'use_correction':True,'df_correction':True},use_t=True)
rows=[];contrasts=[];checks=[]
for kind,flex in [('extended',False),('hospitality',False),('extended',True),('hospitality',True)]:
    X0=matrix(kind,flex);X1=matrix(kind,flex,ex);m0=sm.OLS(y,X0).fit();m1=robust(X1)
    lo,hi=m1.conf_int().loc['cafe'];beta=m1.params['cafe']
    name=kind+('_quadratic_context' if flex else '')
    r={'model':name,'n':len(d),'beta_pp':beta,'ci_lower':lo,'ci_upper':hi,'r2_context':m0.rsquared,'r2_with_cafe':m1.rsquared,'delta_r2':m1.rsquared-m0.rsquared,'partial_r2':(m0.ssr-m1.ssr)/m0.ssr,'rmse_context_pp':np.sqrt(m0.ssr/len(d)),'rmse_with_cafe_pp':np.sqrt(m1.ssr/len(d)),'p':m1.pvalues['cafe']}
    rows.append(r)
    if not flex:
        for label,a,b in [('Observed Q25 to Q75',*d.cafe_per_10k.quantile([.25,.75]).values),('0 to 1 cafes per 10000',0,1),('0 to 5 cafes per 10000',0,5)]:
            delta=np.log2(1+b)-np.log2(1+a)
            contrasts.append({'model':kind,'contrast':label,'density_from':a,'density_to':b,'log2_1plus_difference':delta,'difference_pp':beta*delta,'ci_lower':lo*delta,'ci_upper':hi*delta})
        # Independently remove county means, then regress against context residuals.
        z=d[['cafe_log','MHLTH_CrudePrev']+COV+(['noncafe_log'] if kind=='hospitality' else [])].astype(float)
        z=z-z.groupby(d.countyfips).transform('mean');A=z.iloc[:,2:].to_numpy();xx=z.cafe_log.to_numpy();yy=z.MHLTH_CrudePrev.to_numpy()
        rx=xx-A@np.linalg.lstsq(A,xx,rcond=None)[0];ry=yy-A@np.linalg.lstsq(A,yy,rcond=None)[0]
        b=(rx@ry)/(rx@rx);sse_reduction=(rx@ry)**2/(rx@rx)
        assert abs(b-beta)<1e-9 and abs(sse_reduction-(m0.ssr-m1.ssr))<1e-7
        checks.append({'model':kind,'fwl_beta':b,'statsmodels_beta':beta,'independent_sse_reduction':sse_reduction,'model_sse_reduction':m0.ssr-m1.ssr,'pass':True})
adult=np.log2(1+d.cafe_count/d.TotalPop18plus*10000)
ma=robust(matrix('extended',False,adult));lo,hi=ma.conf_int().loc['cafe']
pd.DataFrame([{'model':'2020 adult denominator sensitivity','n':len(d),'beta_pp':ma.params['cafe'],'ci_lower':lo,'ci_upper':hi,'p':ma.pvalues['cafe']}]).to_csv(DEST/'adult_denominator_sensitivity.csv',index=False)
pd.DataFrame(rows).to_csv(DEST/'incremental_contribution.csv',index=False)
pd.DataFrame(contrasts).to_csv(DEST/'absolute_contrasts.csv',index=False)
pd.DataFrame(checks).to_csv(DEST/'independent_model_checks.csv',index=False)
cv=[];alloc=[]
for block in [5000,20000]:
    cells=(np.floor(d.x_m/block).astype(int).astype(str)+'_'+np.floor(d.y_m/block).astype(int).astype(str))
    folds=pd.Series(-1,index=d.index,dtype=int);rng=np.random.default_rng(20260916)
    for county,idx in d.groupby('countyfips').groups.items():
        unique=np.array(sorted(cells.loc[idx].unique()));rng.shuffle(unique)
        # Small counties can have fewer than five 20-km cells; two suffice
        # for county effects to remain estimable in each occupied test fold.
        assert len(unique)>=2
        mapping={c:i%5 for i,c in enumerate(unique)};folds.loc[idx]=cells.loc[idx].map(mapping)
    alloc.extend({'GEOID':d.GEOID[i],'countyfips':d.countyfips[i],'block_m':block,'cell':cells[i],'fold':int(folds[i])} for i in d.index)
    for kind in ['extended','hospitality']:
        X0=matrix(kind).to_numpy();X1=matrix(kind,exposure=ex).to_numpy()
        p0=np.zeros(len(d));p1=np.zeros(len(d))
        for k in range(5):
            test=(folds==k).to_numpy();train=~test
            assert set(d.countyfips[test])<=set(d.countyfips[train])
            assert not set(zip(d.countyfips[train],cells[train]))&set(zip(d.countyfips[test],cells[test]))
            p0[test]=X0[test]@np.linalg.lstsq(X0[train],y[train],rcond=None)[0]
            p1[test]=X1[test]@np.linalg.lstsq(X1[train],y[train],rcond=None)[0]
            cv.append({'block_m':block,'model':kind,'fold':k,'n':int(test.sum()),'rmse_context_pp':float(np.sqrt(np.mean((y[test]-p0[test])**2))),'rmse_with_cafe_pp':float(np.sqrt(np.mean((y[test]-p1[test])**2)))})
        cv.append({'block_m':block,'model':kind,'fold':'pooled','n':len(d),'rmse_context_pp':float(np.sqrt(np.mean((y-p0)**2))),'rmse_with_cafe_pp':float(np.sqrt(np.mean((y-p1)**2)))})
pd.DataFrame(cv).to_csv(DEST/'spatial_grouped_prediction.csv',index=False)
pd.DataFrame(alloc).to_csv(DEST/'prediction_fold_allocations.csv',index=False)
summary={'sample_n':len(d),'exposure_density_quantiles':d.cafe_per_10k.quantile([0,.25,.5,.75,.9,.99,1]).to_dict(),'health_mean':y.mean(),'health_sd':y.std(ddof=1),'health_iqr':np.quantile(y,.75)-np.quantile(y,.25),'interpretation':'All inference and prediction conditional on modeled PLACES estimates; no independent outcome validation or causal identification.'}
(DEST/'model_diagnostics_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(pd.DataFrame(rows).to_string(index=False));print(pd.DataFrame(cv).query('fold == "pooled"').to_string(index=False));print('PASS independent FWL and spatial allocation checks',flush=True)
