"""Publication figures from retained analytical rows; no generated imagery."""
from pathlib import Path
import pandas as pd,numpy as np,geopandas as gpd,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
ROOT=Path(__file__).resolve().parents[1];figdir=ROOT/'02_Figures';tab=ROOT/'03_Tables'
figdir.mkdir(parents=True, exist_ok=True)
d=gpd.read_parquet(ROOT/'05_Data/processed/analysis_with_predictions.parquet')
cart=gpd.read_parquet(ROOT/'05_Data/processed/study_tracts.parquet')
geo=cart[['GEOID','geometry']].merge(d.drop(columns='geometry'),on='GEOID',validate='one_to_one').to_crs(5070)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':11,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':10,'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
def save(fig,name):
 for ext,dpi in [('pdf',None),('png',350),('tiff',600)]:fig.savefig(figdir/(name+'.'+ext),dpi=dpi,bbox_inches='tight',facecolor='white')
 plt.close(fig)
# Figure 1: three largest counties chosen by resident population, common within-row scales.
selected=pd.read_csv(ROOT/'05_Data/processed/selected_counties.csv',dtype={'STCNTY':str}).head(3)
fig,axs=plt.subplots(3,2,figsize=(7.4,9.0),layout='constrained')
for row,(var,title,cmap) in enumerate([('cafe_per_10k','Mapped cafes per 10,000 residents','viridis'),('MHLTH_CrudePrev','Frequent mental distress (%)','magma')]):
 vmax=float(d[var].quantile(.99)) if row==0 else float(d[var].quantile(.99));vmin=0 if row==0 else float(d[var].quantile(.01))
 for col,c in enumerate(selected.itertuples()):
  dd=geo[geo.countyfips==c.STCNTY];dd.plot(column=var,ax=axs[col,row],cmap=cmap,vmin=vmin,vmax=vmax,edgecolor='none')
  axs[col,row].set_title(f'{chr(65+col*2+row)}  {c.COUNTY.replace(" County","")}, {c.ST_ABBR}');axs[col,row].set_axis_off()
  x0,y0,x1,y1=dd.total_bounds;target=(x1-x0)*.23;length=min([z for z in [1000,2000,5000,10000,20000,50000,100000] if z>=target],default=100000)
  bx=x0+(x1-x0)*.05;by=y0+(y1-y0)*.04
  axs[col,row].plot([bx,bx+length],[by,by],color='black',lw=1.7)
  axs[col,row].text(bx+length/2,by+(y1-y0)*.016,f'{length/1000:g} km',ha='center',fontsize=7,bbox={'facecolor':'white','edgecolor':'none','alpha':.8,'pad':1})
 cb=fig.colorbar(ScalarMappable(norm=Normalize(vmin,vmax),cmap=cmap),ax=list(axs[:,row]),orientation='horizontal',fraction=.018,pad=.025,extend='max' if row==0 else 'both');cb.set_label(title,fontsize=9)
save(fig,'Figure_1_tract_maps')
# All-county sampling frame supplement.
counties=gpd.read_parquet(ROOT/'05_Data/processed/study_counties.parquet').to_crs(5070)
background=gpd.read_file(ROOT/'05_Data/raw/counties_2023.zip');background=background[~background.STATEFP.isin(['02','15','60','66','69','72','78'])].dissolve(by='STATEFP').to_crs(5070)
fig,ax=plt.subplots(figsize=(10,6));background.plot(ax=ax,color='#edf0f2',edgecolor='#afbfc7',linewidth=.4);counties.plot(ax=ax,color='#176b87',edgecolor='#183446',linewidth=.35)
ax.set_axis_off()
# Restrict the locator to the actual study extent, as requested in the journal guide.
x0,y0,x1,y1=counties.total_bounds;ax.set_xlim(x0,x1);ax.set_ylim(y0,y1)
save(fig,'Figure_S1_study_counties')
# Figure 2: primary coefficient across the four prespecified model specifications.
results=pd.read_csv(tab/'Table_2_all_outcome_models.csv')
primary=results[results.outcome=='MHLTH'].set_index('model').loc[['unadjusted','context','extended','hospitality']]
primary.to_csv(tab/'Figure_2_adjustment_data.csv')
fig,ax=plt.subplots(figsize=(7.2,3.9));yy=np.arange(4)
for i,(model,r) in enumerate(primary.iterrows()):
 color='#a94627' if model=='extended' else '#176b87'
 ax.errorbar(r.beta_pp,i,xerr=[[r.beta_pp-r.ci_lower],[r.ci_upper-r.beta_pp]],fmt='o',ms=5,color=color,capsize=3)
labels=['Unadjusted','County and population density','Extended contextual model','Extended + other hospitality']
ax.set_yticks(yy,labels);ax.invert_yaxis();ax.set_ylim(3.5,-.6);ax.axvline(0,color='#333',lw=.8);ax.grid(axis='x',alpha=.15)
ax.set_xlim(-.59,.03);ax.set_xlabel('Mental-distress difference (percentage points)\nper one-unit increase in log2(1 + cafes per 10,000 residents)')
for i,r in enumerate(primary.itertuples()):ax.annotate(f'{r.beta_pp:.3f}',(r.beta_pp,i),xytext=(0,-17),textcoords='offset points',ha='center',fontsize=9)
fig.tight_layout();save(fig,'Figure_2_primary_adjustment')
# Figure 3 forest plot compares common exposure units across eight outcomes.
results=pd.read_csv(tab/'Table_2_all_outcome_models.csv');order=list(results.outcome.drop_duplicates());y=np.arange(len(order))
fig,ax=plt.subplots(figsize=(7.5,6.1))
for model,offset,color,label in [('unadjusted',-.12,'#6e8194','Unadjusted'),('extended',.12,'#a94627','County and covariates adjusted')]:
 r=results[results.model==model].set_index('outcome').loc[order]
 ax.errorbar(r.beta_pp,y+offset,xerr=np.array([r.beta_pp-r.ci_lower,r.ci_upper-r.beta_pp]),fmt='o' if model=='unadjusted' else 's',ms=4,color=color,capsize=2,label=label)
ax.set_yticks(y,[results[results.outcome==o].outcome_label.iloc[0] for o in order]);ax.invert_yaxis();ax.axvline(0,color='#333',lw=.7);ax.grid(axis='x',alpha=.15)
ax.set_xlabel('Difference in modeled prevalence (percentage points)\nper one-unit increase in log2(1 + cafes per 10,000 residents)');ax.legend(loc='lower center',bbox_to_anchor=(.5,1.02),ncol=2,fontsize=8,frameon=False)
fig.tight_layout()
save(fig,'Figure_3_outcome_associations')
# Figure 4 covariate associations, standardized only for comparable display.
c=pd.read_csv(tab/'Table_S2_covariate_coefficients.csv');c['abs']=c.beta_per_sd_pp.abs();c=c.sort_values('abs')
names={'cafe_log':'Mapped cafe availability','log_pop_density':'Resident population density','EP_POV150':'Poverty below 150% threshold','EP_UNEMP':'Unemployment','EP_NOHSDP':'No high-school diploma','EP_AGE65':'Population aged 65+','EP_AGE17':'Population aged 0–17','EP_MINRTY':'Racial/ethnic minority share','EP_NOVEH':'Households without a vehicle'}
fig,ax=plt.subplots(figsize=(7.5,5.8));yy=np.arange(len(c));ax.errorbar(c.beta_per_sd_pp,yy,xerr=np.array([c.beta_per_sd_pp-c.lower_per_sd_pp,c.upper_per_sd_pp-c.beta_per_sd_pp]),fmt='o',color='#176b87',capsize=2)
ax.set_yticks(yy,[names[x] for x in c.term]);ax.axvline(0,color='#333',lw=.7);ax.grid(axis='x',alpha=.15);ax.set_xlabel('Modeled mental-distress difference (percentage points) per 1 SD')
fig.tight_layout()
save(fig,'Figure_4_contextual_correlates')
# Figure 5 no hidden extrapolation above the observed 99th percentile.
c=pd.read_csv(tab/'Figure_4_curve_data.csv');fig,ax=plt.subplots(figsize=(7.7,5.1))
ax.fill_between(c.cafe_per_10k,c.ci_lower,c.ci_upper,color='#176b87',alpha=.18,label='95% conditional interval')
ax.plot(c.cafe_per_10k,c.difference_pp_vs_zero,color='#176b87',lw=2,label='Exploratory quadratic fit');ax.axhline(0,color='#333',lw=.7)
ax.set_xlabel('Mapped cafes per 10,000 residents');ax.set_ylabel('Modeled mental-distress difference\nversus zero mapped cafes (percentage points)');ax.grid(alpha=.15);ax.legend(fontsize=8)
fig.tight_layout()
save(fig,'Figure_5_association_shape')
# Exposure distributions: valid zeros remain visible.
fig,axs=plt.subplots(1,2,figsize=(9,4));axs[0].hist(d.cafe_count.clip(upper=20),bins=np.arange(-.5,21.5,1),color='#176b87');axs[0].set_xlabel('Mapped cafes per tract (20 includes 20+)');axs[0].set_ylabel('Number of tracts')
axs[1].hist(d.cafe_log,bins=40,color='#a94627');axs[1].set_xlabel('log2(1 + mapped cafes per 10,000 residents)');axs[1].set_ylabel('Number of tracts')
for i,ax in enumerate(axs):ax.text(.01,.98,chr(65+i),transform=ax.transAxes,va='top',fontweight='bold')
fig.tight_layout();save(fig,'Figure_S2_exposure_distribution')
print('FIGURES COMPLETE',flush=True)
