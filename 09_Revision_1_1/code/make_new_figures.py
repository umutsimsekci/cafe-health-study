from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd,numpy as np
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1];D=BASE.parent/'results';F=D/'Figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'savefig.dpi':300})
COLORS=['#167D8D','#A05B3D']
m=pd.read_csv(D/'incremental_contribution.csv').set_index('model').loc[['extended','hospitality']]
c=pd.read_csv(D/'spatial_grouped_prediction.csv');c=c[(c.fold=='pooled')&(c.block_m==5000)].set_index('model').loc[m.index]
fig,ax=plt.subplots(1,2,figsize=(10.2,3.8));labels=['Extended\ncontext','Extended context\n+ hospitality']
for j,(vals,title,xlabel) in enumerate([(m.delta_r2*100,'A  Additional variance explained','Increase in R² (percentage points)'),(c.rmse_context_pp-c.rmse_with_cafe_pp,'B  Held-out prediction improvement','Reduction in RMSE (prevalence points)')]):
    ax[j].barh([1,0],vals,color=COLORS,height=.48)
    ax[j].set_yticks([1,0],labels);ax[j].set_xlabel(xlabel);ax[j].set_title(title,loc='left',pad=14)
    lim=max(vals)*1.36;ax[j].set_xlim(0,lim);ax[j].set_ylim(-.65,1.65)
    ax[j].grid(axis='x',alpha=.15);ax[j].set_axisbelow(True)
    for y,v in zip([1,0],vals):ax[j].text(v+lim*.025,y,f'{v:.4f}' if j else f'{v:.3f}',va='center')
    ax[j].spines['left'].set_visible(False);ax[j].tick_params(axis='y',length=0)
fig.subplots_adjust(left=.14,right=.99,bottom=.23,top=.84,wspace=.75)
fig.text(.14,.035,'Same 23,527 tracts. Panel B: five folds of 5-km cells within counties. Outcomes are PLACES estimates.',fontsize=9,color='#444444')
for ext in ['pdf','png']:fig.savefig(F/('Figure_6_incremental_contribution.'+ext),bbox_inches='tight')
plt.close(fig)
s=pd.read_csv(D/'chicago_concordance_summary.csv');s=s[s.poverty_stratum.eq('All')]
fig,ax=plt.subplots(1,2,figsize=(9.8,4.3))
for j,(comparison,title,denom) in enumerate([('OSM cafe to eligible license','A  OSM cafes linked to licenses',742),('Coffee-named license to OSM cafe','B  Coffee-named licenses linked to OSM cafes',281)]):
    q=s[s.comparison.eq(comparison)].sort_values('maximum_distance_m');pos=np.arange(3)
    ax[j].bar(pos,q.concordance_percent,color=COLORS[j],width=.58)
    ax[j].set_ylim(0,100);ax[j].set_xticks(pos,[str(x)+' m' for x in q.maximum_distance_m]);ax[j].set_xlabel('Maximum matching distance')
    ax[j].set_ylabel('Records linked (%)');ax[j].set_title(title,loc='left',fontsize=10.5,pad=18)
    ax[j].grid(axis='y',alpha=.18);ax[j].set_axisbelow(True)
    for x,row in zip(pos,q.itertuples()):ax[j].text(x,row.concordance_percent+2,f'{row.linked_n}/{row.denominator}\n({row.concordance_percent:.1f}%)',ha='center',fontsize=9)
fig.subplots_adjust(left=.075,right=.98,top=.83,bottom=.25,wspace=.32)
fig.text(.075,.055,'Chicago historical record concordance. Name rules also apply.\nNeither source is a gold standard; percentages do not estimate national cafe completeness.',fontsize=9,color='#444444')
for ext in ['pdf','png']:fig.savefig(F/('Figure_S3_chicago_record_concordance.'+ext),bbox_inches='tight')
plt.close(fig)
print(F)
