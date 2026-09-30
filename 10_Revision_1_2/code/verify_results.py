"""Reproduce new regression results with statsmodels and check prediction tables.

Run verify_proximity.py separately for independent all-pairs/geodesic counts.
This script uses archived proximity counts but an independent OLS/covariance
implementation, rather than the county-demeaned score calculation.
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
COV=['log_pop_density','EP_POV150','EP_UNEMP','EP_NOHSDP','EP_AGE65','EP_AGE17','EP_MINRTY','EP_NOVEH']

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=ROOT/'05_Data')
 ap.add_argument('--results',type=Path,default=BASE.parent/'results')
 args=ap.parse_args();results=args.results
 d=pd.read_csv(args.source/'processed/analysis_dataset.csv',dtype={'GEOID':str,'countyfips':str})
 p=pd.read_csv(results/'nearby_cafe_exposure.csv',dtype={'GEOID':str,'countyfips':str})
 assert len(d)==23527 and d.GEOID.is_unique and d.GEOID.equals(p.GEOID)
 assert d.countyfips.equals(p.countyfips)
 np.testing.assert_array_equal(d.cafe_count,p.own_tract_cafe_count)
 assert p.coverage_verified_1000m.all()
 summary=pd.read_csv(results/'nearby_cafe_summary.csv')
 models=pd.read_csv(results/'nearby_cafe_models.csv')
 fe=pd.get_dummies(d.countyfips,prefix='county',drop_first=True,dtype=float)
 modelchecks=[]
 for radius in [500,1000]:
  counts=p[f'mapped_cafes_within_{radius}m'];extra=p[f'mapped_noncafe_hospitality_within_{radius}m']
  assert counts.ge(0).all() and counts.le(p.mapped_cafes_within_1000m).all()
  zero=p.own_tract_cafe_count.eq(0);nearby=counts.gt(0)
  np.testing.assert_array_equal(p[f'own_tract_zero_nearby_{radius}m'],zero&nearby)
  s=summary[summary.radius_m.eq(radius)].iloc[0]
  assert int(s.zero_own_tract_but_nearby_cafe)==int((zero&nearby).sum())
  assert int(s.own_tract_cafe_but_no_centroid_nearby_cafe)==int((~zero&~nearby).sum())
  assert (p[f'mapped_cafes_across_tract_boundary_{radius}m']<=counts).all()
  for kind in ['context','context_nearby_hospitality']:
   X=d[COV].copy()
   if kind.endswith('hospitality'):X['hospitality']=np.log2(1+extra)
   X=pd.concat([X,fe],axis=1);X=sm.add_constant(X,has_constant='add')
   m0=sm.OLS(d.MHLTH_CrudePrev,X).fit()
   X['cafe']=np.log2(1+counts)
   m=sm.OLS(d.MHLTH_CrudePrev,X).fit(cov_type='cluster',cov_kwds={'groups':d.countyfips,'use_correction':True,'df_correction':True},use_t=True)
   r=models[models.radius_m.eq(radius)&models.model.eq(kind)].iloc[0]
   lo,hi=m.conf_int().loc['cafe']
   np.testing.assert_allclose([m.params.cafe,m.bse.cafe,lo,hi,m.rsquared,m.rsquared-m0.rsquared],
                             [r.beta_pp,r.se_county_cluster_pp,r.ci_lower,r.ci_upper,r.r2_with_cafes,r.delta_r2],atol=1e-10,rtol=0)
   modelchecks.append({'radius_m':radius,'model':kind,'statsmodels_beta_pp':float(m.params.cafe),'statsmodels_se_pp':float(m.bse.cafe),'passed':True})
 preds=pd.read_csv(results/'buffered_prediction_tract_values.csv',dtype={'GEOID':str,'countyfips':str})
 assert d.GEOID.equals(preds.GEOID) and preds.fold_20km.between(0,4).all()
 cv=pd.read_csv(results/'buffered_spatial_prediction.csv',dtype={'fold':str})
 for radius in [0,1000]:
  for kind in ['extended','hospitality']:
   for fold in ['0','1','2','3','4','pooled']:
    mask=np.ones(len(d),dtype=bool) if fold=='pooled' else preds.fold_20km.eq(int(fold)).to_numpy()
    p0=preds[f'pred_{kind}_context_buffer_{radius}m'];p1=preds[f'pred_{kind}_cafes_buffer_{radius}m']
    rm0=np.sqrt(np.mean((d.MHLTH_CrudePrev[mask]-p0[mask])**2));rm1=np.sqrt(np.mean((d.MHLTH_CrudePrev[mask]-p1[mask])**2))
    r=cv[cv.buffer_m.eq(radius)&cv.model.eq(kind)&cv.fold.eq(fold)].iloc[0]
    assert int(r.n_test)==int(mask.sum())
    np.testing.assert_allclose([rm0,rm1,rm0-rm1],[r.rmse_context_pp,r.rmse_with_cafe_pp,r.rmse_improvement_pp],atol=1e-10,rtol=0)
 figure=pd.read_csv(results/'Figure_4_measurement_classification_data.csv')
 assert (figure.at_least_one_mapped_cafe+figure.no_mapped_cafe).equals(figure.denominator_tracts)
 np.testing.assert_allclose(figure.at_least_one_percent+figure.no_mapped_cafe_percent,100,atol=1e-10)
 result={'passed':True,'model_checks':modelchecks,
         'checks':['Unique tract identities and county alignment','Original tract cafe counts retained','Nested radius counts and boundary/zero identities',
                   'Independent statsmodels coefficient and CR1 standard error with full county dummy matrix',
                   'All fold and pooled RMSEs reproduced from archived held-out predictions','Figure4 exhaustive counts and percentages'],
         'limitations':'These checks confirm reproducibility. They do not establish independent observed health validity, joint source uncertainty, walking access, or causal effects.'}
 (results/'verification_receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print('PASS',json.dumps(result))

if __name__=='__main__':main()
