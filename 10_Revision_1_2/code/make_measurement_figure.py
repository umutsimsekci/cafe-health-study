"""Figure4 from archived centroid-proximity classifications, without refitting."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

BASE=Path(__file__).resolve().parent
REVISION=BASE.parent
RESULTS=REVISION/'results'
OUT=REVISION/'figures'
OUT.mkdir(parents=True,exist_ok=True)

def main():
    d=pd.read_csv(RESULTS/'nearby_cafe_exposure.csv',dtype={'GEOID':str,'countyfips':str})
    assert len(d)==23527 and d.GEOID.is_unique
    zero=d.own_tract_cafe_count.eq(0);nzero=int(zero.sum())
    rows=[]
    for panel,label,v in [
        ('A','Within own tract',d.own_tract_cafe_count.gt(0)),
        ('A','Within 500 m of centroid',d.mapped_cafes_within_500m.gt(0)),
        ('A','Within 1 km of centroid',d.mapped_cafes_within_1000m.gt(0)),
        ('B','Within 500 m of centroid',d.loc[zero,'mapped_cafes_within_500m'].gt(0)),
        ('B','Within 1 km of centroid',d.loc[zero,'mapped_cafes_within_1000m'].gt(0))]:
        n=len(v);yes=int(v.sum());no=n-yes
        rows.append({'panel':panel,'availability_rule':label,'denominator_tracts':n,
                     'at_least_one_mapped_cafe':yes,'no_mapped_cafe':no,
                     'at_least_one_percent':100*yes/n,'no_mapped_cafe_percent':100*no/n})
    table=pd.DataFrame(rows)
    table.to_csv(RESULTS/'Figure_4_measurement_classification_data.csv',index=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42,
                         'axes.labelsize':10,'axes.titlesize':12,'xtick.labelsize':9,
                         'ytick.labelsize':10})
    blue='#22688B';gray='#DFE4E7';text='#18262D'
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),gridspec_kw={'width_ratios':[1,1]})
    for ax,panel,title in zip(axes,['A','B'],['All 23,527 study tracts','17,331 tracts with no cafe inside their boundary']):
        data=table[table.panel.eq(panel)].reset_index(drop=True)
        y=list(range(len(data)))
        ax.barh(y,data.at_least_one_percent,color=blue,height=.34)
        ax.barh(y,data.no_mapped_cafe_percent,left=data.at_least_one_percent,color=gray,height=.34)
        for i,r in data.iterrows():
            # Text above the bar keeps small positive categories readable.
            ax.text(0,i-.25,f"{r.at_least_one_mapped_cafe:,} ({r.at_least_one_percent:.1f}%)",color=blue,
                    fontsize=9,va='center',ha='left',fontweight='bold')
            ax.text(100,i-.25,f"{r.no_mapped_cafe:,} ({r.no_mapped_cafe_percent:.1f}%)",color=text,
                    fontsize=9,va='center',ha='right')
        ax.set_yticks(y,data.availability_rule)
        ax.set_ylim(-.6,len(data)-.55);ax.invert_yaxis()
        ax.set_xlim(0,100);ax.set_xticks([0,25,50,75,100])
        ax.set_xlabel('Percentage of tracts in the indicated sample')
        ax.set_title(f'{panel}  {title}',loc='left',pad=17,fontsize=11)
        for spine in ['top','right','left']:ax.spines[spine].set_visible(False)
        ax.spines['bottom'].set_color('#ADB9BF');ax.tick_params(axis='y',length=0,pad=7)
        ax.grid(axis='x',color='#EDF0F2',lw=.7,zorder=0);ax.set_axisbelow(True)
    # Titles and categories intentionally wrap for clear panel widths.
    axes[1].set_title('B  No mapped cafe inside the tract boundary\n     n = 17,331',loc='left',pad=12,fontsize=11)
    fig.legend(handles=[Patch(facecolor=blue,label='At least one mapped cafe under the stated rule'),
                        Patch(facecolor=gray,label='No mapped cafe under the stated rule')],
               loc='lower center',bbox_to_anchor=(.52,.035),ncol=1,frameon=False,fontsize=9)
    fig.subplots_adjust(left=.19,right=.985,top=.80,bottom=.27,wspace=.80)
    fig.savefig(OUT/'Figure_4_measurement_classification.pdf',bbox_inches='tight',metadata={'Title':'Mapped cafe classification under tract and centroid proximity rules'})
    fig.savefig(OUT/'Figure_4_measurement_classification.png',dpi=300,bbox_inches='tight')
    plt.close(fig)
    caption=('Figure 4. Mapped cafe classification under tract and centroid proximity rules. '
             'Panel A uses all 23,527 study tracts; panel B uses the 17,331 tracts with no mapped cafe within their own boundary. '
             'Bars exhaustively classify each indicated sample into at least one mapped cafe or none under each rule. '
             'Centroid proximity counts use EPSG:5070 planar distances of 500 m or 1 km from the frozen full-resolution geometric tract centroid. '
             'The same December 2022 nonduplicate OSM inventory is used, including records in excluded or adjacent tracts. '
             'These counts describe geographical measurement and do not measure walking access, residential exposure, cafe attendance, or a health intervention. '
             'Source: © OpenStreetMap contributors, 31 December 2022 snapshot; US Census Bureau tract geography. '
             'The 500 m and 1 km calculations are exploratory post-results analyses.')
    (RESULTS/'Figure_4_caption.txt').write_text(caption+'\n',encoding='utf-8')
    print(table.to_string(index=False))

if __name__=='__main__':main()
