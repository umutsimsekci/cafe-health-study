"""Reproduce the four primary-outcome OLS models from the compact public CSV."""
from pathlib import Path
import json, os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import numpy as np
import pandas as pd
import statsmodels.api as sm

root=Path(__file__).resolve().parents[1]
d=pd.read_csv(root/'05_Data/processed/analysis_dataset.csv.gz',dtype={'GEOID':str,'countyfips':str})
reference=pd.read_csv(root/'03_Tables/Table_2_all_outcome_models.csv')
cov=['log_pop_density','EP_POV150','EP_UNEMP','EP_NOHSDP','EP_AGE65','EP_AGE17','EP_MINRTY','EP_NOVEH']
assert len(d)==23527 and d.countyfips.nunique()==50
assert int(d.cafe_count.sum())==13195 and int(d.E_TOTPOP.sum())==99313722
checks=[]
for name in ['unadjusted','context','extended','hospitality']:
    columns=['cafe_log'] + (cov[:1] if name=='context' else cov if name in ['extended','hospitality'] else [])
    if name=='hospitality': columns+=['noncafe_log']
    x=d[columns].astype(float)
    if name!='unadjusted':x=pd.concat([x,pd.get_dummies(d.countyfips,prefix='county',drop_first=True,dtype=float)],axis=1)
    x=sm.add_constant(x,has_constant='add')
    result=sm.OLS(d.MHLTH_CrudePrev.astype(float),x).fit(cov_type='cluster',cov_kwds={'groups':d.countyfips,'use_correction':True,'df_correction':True},use_t=True)
    actual=np.array([result.params['cafe_log'],*result.conf_int().loc['cafe_log']])
    expected=reference[(reference.outcome=='MHLTH')&(reference.model==name)].iloc[0][['beta_pp','ci_lower','ci_upper']].to_numpy(dtype=float)
    assert np.allclose(actual,expected,rtol=1e-8,atol=1e-10),(name,actual,expected)
    checks.append({'model':name,'beta_pp':actual[0],'ci_lower':actual[1],'ci_upper':actual[2],'matches_archive':True})
print(json.dumps({'n':len(d),'counties':50,'primary_models':checks,'interpretation':'Conditional ecological associations, not causal effects.'},indent=2))
