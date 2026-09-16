from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1];D=BASE.parent/'results'
o=pd.read_csv(D/'chicago_osm_record_audit.csv',dtype={'linked_license':str,'GEOID':str})
a=pd.read_csv(D/'chicago_eligible_license_audit.csv',dtype={'license_number':str})
links=pd.read_csv(D/'chicago_accepted_links.csv',dtype={'license_number':str})
assert links.osm_id.is_unique and links.license_number.is_unique
assert (links.distance_m<=100).all() and (links.name_score>=.88).all()
assert set(links.license_number)<=set(a.license_number)
assert (a.temporal_eligible==True).all()
assert not o.loc[o.linked_license.isna(),'linked_nonlicensing_2022_inspection'].any()
cafe=o[o.amenity=='cafe'];assert cafe.linked_nonlicensing_2022_inspection.sum()<=cafe.linked_license.notna().sum()
summary=pd.read_csv(D/'chicago_concordance_summary.csv')
for r in summary[(summary.maximum_distance_m==100)&summary.poverty_stratum.eq('All')].itertuples():
    if r.comparison.startswith('OSM'):n=len(cafe);k=cafe.linked_license.notna().sum()
    else:
        dd=a[a.coffee_named_subset if r.comparison.startswith('Coffee') else a.broad_cafe_named_subset];n=len(dd);k=dd.linked_osm_amenity.eq('cafe').sum()
    assert n==r.denominator and k==r.linked_n and abs(100*k/n-r.concordance_percent)<1e-10
m=pd.read_csv(D/'incremental_contribution.csv')
assert np.allclose(m.delta_r2,m.r2_with_cafe-m.r2_context)
assert np.allclose(m.partial_r2,m.delta_r2/(1-m.r2_context))
c=pd.read_csv(D/'absolute_contrasts.csv')
for r in c.itertuples():
    b=m.set_index('model').loc[r.model];delta=np.log2((1+r.density_to)/(1+r.density_from))
    assert abs(r.difference_pp-b.beta_pp*delta)<1e-12
rec={'passed':True,'checks':['Unique one-to-one links','Temporal eligibility','Distance/name rules','Missing licenses never counted as inspection confirmation','Independent recomputation of all aggregate100m concordance rates','Nested R2/partial R2 identities','Absolute contrasts from coefficients and density ratios'],'limitations':'Numerical consistency and inspectable record concordance do not constitute field validation or independent health validation.'}
(D/'new_result_verification.json').write_text(json.dumps(rec,indent=2)+'\n',encoding='utf-8')
print('PASS',json.dumps(rec))
