"""Exploratory boundary and buffered-prediction checks on frozen 2022 data.

This does not modify any original study data. Thresholds and specifications
are documented in exploratory_plan.json before fitting the new models.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
HERE = BASE.parent / 'results'
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from scipy import stats

DEFAULT_SOURCE = ROOT / '05_Data'
COV = ['log_pop_density', 'EP_POV150', 'EP_UNEMP', 'EP_NOHSDP',
       'EP_AGE65', 'EP_AGE17', 'EP_MINRTY', 'EP_NOVEH']

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def fit_within(d, exposure, extra=None):
    """County-FE OLS with independently accumulated CR1 county sandwich."""
    x = d[COV].copy()
    if extra is not None: x['hospitality'] = extra
    x['cafe'] = exposure
    county = d.countyfips
    xx = (x - x.groupby(county).transform('mean')).to_numpy()
    yy = (d.MHLTH_CrudePrev - d.MHLTH_CrudePrev.groupby(county).transform('mean')).to_numpy()
    beta = np.linalg.lstsq(xx, yy, rcond=None)[0]
    residual = yy - xx @ beta
    bread = np.linalg.inv(xx.T @ xx)
    scores = pd.DataFrame(xx * residual[:,None]).groupby(county).sum().to_numpy()
    g = county.nunique(); n = len(d); k = g + xx.shape[1]
    vc = bread @ (scores.T @ scores) @ bread * (g/(g-1)) * ((n-1)/(n-k))
    se = float(np.sqrt(vc[-1,-1])); b = float(beta[-1]); crit = stats.t.ppf(.975,g-1)
    # Full-model R2 uses between-county variation in the original outcome.
    sst = float(np.sum((d.MHLTH_CrudePrev-d.MHLTH_CrudePrev.mean())**2))
    sse = float(residual @ residual)
    b0 = np.linalg.lstsq(xx[:,:-1], yy, rcond=None)[0]
    residual0 = yy-xx[:,:-1]@b0; sse0=float(residual0@residual0)
    q25,q75=np.quantile(exposure,[.25,.75]); contrast=float(q75-q25)
    return {'n':n,'counties':int(g),'design_rank':k,'beta_pp':b,
            'se_county_cluster_pp':se,'ci_lower':b-crit*se,'ci_upper':b+crit*se,
            'p':float(2*stats.t.sf(abs(b/se),g-1)),
            'exposure_q25':float(q25),'exposure_q75':float(q75),
            'iqr_difference_pp':b*contrast,'iqr_ci_lower':(b-crit*se)*contrast,
            'iqr_ci_upper':(b+crit*se)*contrast,'r2_without_cafes':1-sse0/sst,
            'r2_with_cafes':1-sse/sst,'delta_r2':(sse0-sse)/sst}

def main():
    global HERE
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=DEFAULT_SOURCE)
    ap.add_argument('--output', type=Path, default=HERE)
    args=ap.parse_args(); source=args.source; HERE=args.output
    HERE.mkdir(parents=True, exist_ok=True)
    plan_path=BASE.parent/'methods/exploratory_plan.json'
    assert plan_path.exists(), 'Exploratory plan missing'
    dpath=source/'processed/analysis_dataset.csv'; ppath=source/'processed/osm_features_assigned.parquet'
    d=pd.read_csv(dpath,dtype={'GEOID':str,'countyfips':str})
    assert len(d)==23527 and d.GEOID.is_unique and d.countyfips.nunique()==50
    p=pd.read_parquet(ppath); p=p[~p.duplicate_representation].copy().reset_index(drop=True)
    assert set(p.snapshot)=={'2022-12-31T23:59:59Z'} and p.osm_id.is_unique
    assigned_counts=p[p.amenity.eq('cafe')].groupby('GEOID').size()
    np.testing.assert_array_equal(d.cafe_count.to_numpy(),d.GEOID.map(assigned_counts).fillna(0).to_numpy())
    xy=d[['x_m','y_m']].to_numpy()
    transform=Transformer.from_crs(4326,5070,always_xy=True)
    back=Transformer.from_crs(5070,4326,always_xy=True)
    px,py=transform.transform(p.longitude.to_numpy(),p.latitude.to_numpy()); points=np.c_[px,py]
    cf=p.amenity.eq('cafe').to_numpy(); cafep=p.loc[cf].copy().reset_index(drop=True)
    cafe_xy=points[cf]; other_xy=points[~cf]
    tree=cKDTree(cafe_xy); other=cKDTree(other_xy)
    nearest,nearidx=tree.query(xy,k=1)
    out=d[['GEOID','countyfips','CountyName','StateAbbr']].copy()
    out['own_tract_cafe_count']=d.cafe_count
    out['nearest_mapped_cafe_m']=nearest
    out['nearest_mapped_cafe_within_1000m_m']=np.where(nearest<=1000,nearest,np.nan)
    out['nearest_mapped_cafe_in_own_tract']=cafep.GEOID.iloc[nearidx].fillna('').to_numpy()==d.GEOID.to_numpy()
    coverage=[]
    # Verify the entire1km circle lies within its original own-county extraction
    # rectangle.64directions at1005m provide a conservative practical margin.
    angles=np.arange(64)*2*np.pi/64
    for county,idx in d.groupby('countyfips').groups.items():
        box=np.array(json.loads((source/'raw/osm_2022'/f'{county}.query.json').read_text())['params']['bboxes'].split(','),dtype=float)
        circ=xy[idx,None,:]+1005*np.c_[np.cos(angles),np.sin(angles)][None,:,:]
        lon,lat=back.transform(circ[:,:,0],circ[:,:,1])
        inside=(lon.min(axis=1)>box[0])&(lat.min(axis=1)>box[1])&(lon.max(axis=1)<box[2])&(lat.max(axis=1)<box[3])
        coverage.extend({'GEOID':d.GEOID[i],'countyfips':county,'coverage_verified_1000m':bool(v)} for i,v in zip(idx,inside))
    cover=pd.DataFrame(coverage).set_index('GEOID').reindex(d.GEOID)
    out['coverage_verified_1000m']=cover.coverage_verified_1000m.to_numpy()
    assert out.coverage_verified_1000m.all(), 'Some1kmcircles exceed original extraction rectangle'
    summaries=[];modelrows=[]
    for r in [500,1000]:
        links=tree.query_ball_point(xy,r,workers=2)
        counts=np.fromiter((len(v) for v in links),dtype=int,count=len(d))
        nc=other.query_ball_point(xy,r,return_length=True,workers=2)
        outside=np.array([sum(cafep.GEOID.iloc[v].fillna('').to_numpy()!=d.GEOID.iloc[i]) for i,v in enumerate(links)])
        out[f'mapped_cafes_within_{r}m']=counts
        out[f'mapped_noncafe_hospitality_within_{r}m']=nc
        out[f'mapped_cafes_across_tract_boundary_{r}m']=outside
        zero=d.cafe_count.eq(0).to_numpy(); available=counts>0
        out[f'own_tract_zero_nearby_{r}m']=zero&available
        summaries.append({'radius_m':r,'tracts':len(d),'zero_own_tract_cafe':int(zero.sum()),
                          'zero_own_tract_but_nearby_cafe':int((zero&available).sum()),
                          'percent_of_zero_tracts_with_nearby_cafe':float(100*(zero&available).sum()/zero.sum()),
                          'any_nearby_cafe_tracts':int(available.sum()),'percent_tracts_any_nearby_cafe':float(100*available.mean()),
                          'own_tract_cafe_but_no_centroid_nearby_cafe':int((~zero&~available).sum()),
                          'tracts_with_any_cross_boundary_cafe':int((outside>0).sum()),
                          'median_nearby_cafe_count':float(np.median(counts)),
                          'q25_nearby_cafe_count':float(np.quantile(counts,.25)),
                          'q75_nearby_cafe_count':float(np.quantile(counts,.75))})
        for model,extra in [('context',None),('context_nearby_hospitality',np.log2(1+nc))]:
            fit=fit_within(d,np.log2(1+counts),extra)
            modelrows.append({'radius_m':r,'model':model,'exposure':'log2(1 + fixed-radius cafe count)',**fit})
    out.to_csv(HERE/'nearby_cafe_exposure.csv',index=False,float_format='%.9f')
    pd.DataFrame(summaries).to_csv(HERE/'nearby_cafe_summary.csv',index=False)
    pd.DataFrame(modelrows).to_csv(HERE/'nearby_cafe_models.csv',index=False)
    check=fit_within(d,d.cafe_log)
    np.testing.assert_allclose(check['beta_pp'],-0.0962589386443312,atol=1e-10,rtol=0)
    np.testing.assert_allclose(check['se_county_cluster_pp'],0.015366013460870164,atol=1e-10,rtol=0)
    check2=fit_within(d,d.cafe_log,d.noncafe_log)
    # Descriptive county slopes. They are not independently validated outcomes.
    slopes=[]
    for county,idx in d.groupby('countyfips').groups.items():
        dc=d.loc[idx];X=np.c_[np.ones(len(dc)),dc[COV],dc.cafe_log]
        b=np.linalg.lstsq(X,dc.MHLTH_CrudePrev,rcond=None)[0]
        slopes.append({'countyfips':county,'CountyName':dc.CountyName.iloc[0],'StateAbbr':dc.StateAbbr.iloc[0],
                       'n':len(dc),'cafes':int(dc.cafe_count.sum()),'cafe_log_sd':float(dc.cafe_log.std()),
                       'adjusted_cafe_beta_pp':float(b[-1]),'design_rank':int(np.linalg.matrix_rank(X)),
                       'interpretation':'Exploratory county-specific descriptive OLS; no independent health or causal validation'})
    pd.DataFrame(slopes).to_csv(HERE/'county_descriptive_slopes.csv',index=False)
    # Source / code receipts and a compact summary must precede CV completion,
    # so atlas builder can use proximity data while slower diagnostic runs.
    receipt={'source_csv':'05_Data/processed/analysis_dataset.csv','source_csv_sha256':digest(dpath),
             'source_osm_assignment':'05_Data/processed/osm_features_assigned.parquet','source_osm_assignment_sha256':digest(ppath),
             'retained_cafe_records_all_expanded_queries':len(cafep),'cafes_in_analysis':int(d.cafe_count.sum()),
             'all_tract_1km_query_coverage':bool(out.coverage_verified_1000m.all()),
             'primary_independent_reproduction':check,'hospitality_independent_reproduction':check2,
             'summary':summaries,'proximity_models':modelrows,
             'nearest_distance_warning':'Distances beyond1km use the observed expanded inventory only and are not a verified complete nearest-establishment distance'}
    (HERE/'scientific_results.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(pd.DataFrame(summaries).to_string(index=False),flush=True)
    print(pd.DataFrame(modelrows).to_string(index=False),flush=True)
    # Reuse original20kmfolds; training covariates/coefficients are never fitted
    # using heldout outcomes. County dummies remain estimable in training.
    allocations=pd.read_csv(ROOT/'09_Revision_1_1/results/prediction_fold_allocations.csv',dtype={'GEOID':str,'countyfips':str})
    alloc=allocations[allocations.block_m.eq(20000)].set_index('GEOID').reindex(d.GEOID)
    assert len(alloc)==len(d) and alloc.fold.notna().all()
    folds=alloc.fold.to_numpy(dtype=int)
    fe=pd.get_dummies(d.countyfips,drop_first=True,dtype=float).to_numpy()
    y=d.MHLTH_CrudePrev.to_numpy();cv=[];preds=d[['GEOID','countyfips']].copy();preds['fold_20km']=folds
    for buffer_m in [0,1000]:
        predictions={}
        for kind in ['extended','hospitality']:
            cols=COV+(['noncafe_log'] if kind=='hospitality' else [])
            X0=np.c_[np.ones(len(d)),d[cols],fe];X1=np.c_[X0,d.cafe_log]
            p0=np.zeros(len(d));p1=np.zeros(len(d))
            for fold in range(5):
                test=folds==fold;train=~test
                if buffer_m:
                    distances=cKDTree(xy[test]).query(xy[train],k=1)[0]
                    trainidx=np.flatnonzero(train);train[trainidx[distances<=buffer_m]]=False
                    remaining=cKDTree(xy[test]).query(xy[train],k=1)[0]
                    assert remaining.min()>buffer_m
                assert set(d.countyfips[test])<=set(d.countyfips[train])
                assert np.linalg.matrix_rank(X1[train])==X1.shape[1]
                p0[test]=X0[test]@np.linalg.lstsq(X0[train],y[train],rcond=None)[0]
                p1[test]=X1[test]@np.linalg.lstsq(X1[train],y[train],rcond=None)[0]
                rms0=float(np.sqrt(np.mean((y[test]-p0[test])**2)));rms1=float(np.sqrt(np.mean((y[test]-p1[test])**2)))
                cv.append({'block_m':20000,'buffer_m':buffer_m,'model':kind,'fold':fold,
                           'n_test':int(test.sum()),'n_train':int(train.sum()),
                           'n_removed_for_buffer':int((~test).sum()-train.sum()),
                           'minimum_train_tracts_in_any_county':int(d.countyfips[train].value_counts().min()),
                           'rmse_context_pp':rms0,'rmse_with_cafe_pp':rms1,'rmse_improvement_pp':rms0-rms1})
            rms0=float(np.sqrt(np.mean((y-p0)**2)));rms1=float(np.sqrt(np.mean((y-p1)**2)))
            cv.append({'block_m':20000,'buffer_m':buffer_m,'model':kind,'fold':'pooled','n_test':len(d),
                       'rmse_context_pp':rms0,'rmse_with_cafe_pp':rms1,'rmse_improvement_pp':rms0-rms1})
            preds[f'pred_{kind}_context_buffer_{buffer_m}m']=p0
            preds[f'pred_{kind}_cafes_buffer_{buffer_m}m']=p1
        print(f'Finished20km CV with {buffer_m} m buffer',flush=True)
    cvs=pd.DataFrame(cv)
    prior=pd.read_csv(ROOT/'09_Revision_1_1/results/spatial_grouped_prediction.csv')
    for kind in ['extended','hospitality']:
        old=prior[(prior.block_m.eq(20000))&prior.model.eq(kind)&prior.fold.eq('pooled')].iloc[0]
        new=cvs[cvs.buffer_m.eq(0)&cvs.model.eq(kind)&cvs.fold.eq('pooled')].iloc[0]
        np.testing.assert_allclose([new.rmse_context_pp,new.rmse_with_cafe_pp],[old.rmse_context_pp,old.rmse_with_cafe_pp],atol=1e-9,rtol=0)
    cvs.to_csv(HERE/'buffered_spatial_prediction.csv',index=False)
    preds.to_csv(HERE/'buffered_prediction_tract_values.csv',index=False)
    receipt['buffered_prediction']=cvs[cvs.fold.eq('pooled')].replace({np.nan:None}).to_dict('records')
    receipt['verification']={'frozen_count_assignment_reproduced':True,'original_cluster_coefficient_and_se_reproduced':True,
                             'all1km_querycoverage_verified':True,'original20kmcv_reproduced':True,
                             'buffered_training_centroids_more_than1km_from_all_testcentroids':True}
    (HERE/'scientific_results.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(cvs[cvs.fold.eq('pooled')].to_string(index=False),flush=True)

if __name__=='__main__': main()
