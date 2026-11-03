"""Scientific figures from aggregate plot data; never reads raw outcomes.

Reproduction extra: matplotlib==3.10.7. Runtime benchmark is stdlib-only.
"""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams.update({'svg.hashsalt':'deviation-phase5','font.family':'DejaVu Sans','font.size':10})
p=argparse.ArgumentParser();p.add_argument('artifacts',type=Path);a=p.parse_args()
d=json.loads((a.artifacts/'plot_data.json').read_text())
if d['recorded']:
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    for m in sorted({r['mechanism'] for r in d['recorded']}):
        rs=sorted([r for r in d['recorded'] if r['mechanism']==m],key=lambda r:float(__import__('fractions').Fraction(r['condition'])))
        xs=[float(__import__('fractions').Fraction(r['condition'])) for r in rs];ys=[r['mean_quality'] for r in rs]
        ax.plot(xs,ys,marker='o',label=m)
    ax.set(xlabel='Budget interpolation: cheapest to most expensive train-only reservations',ylabel='Mean judged preference proxy',title='Exploratory recorded outcomes • synthetic forecasting policies')
    ax.set_ylim(0,1);ax.legend(fontsize=8,loc='best');ax.grid(alpha=.2)
    fig.savefig(a.artifacts/'recorded_quality.svg',metadata={'Date':None});plt.close(fig)
if d['recorded']:
    fig,ax=plt.subplots(figsize=(7,5),layout='constrained')
    for m in ['lmsr','calibrated-pool','text-router']:
        row=next(r for r in d['recorded'] if r['mechanism']==m and r['condition']=='1/2')
        bins=[b for b in row['reliability_bins'] if b['count']]
        ax.plot([b['prediction_sum']/b['count'] for b in bins],[b['outcome_sum']/b['count'] for b in bins],marker='o',label=m)
    ax.plot([0,1],[0,1],ls='--',color='gray');ax.legend()
    ax.set(xlabel='Mean predicted preference proxy (five fixed bins)',ylabel='Mean observed judged proxy',title='Descriptive reliability • recorded validation, midpoint budget',xlim=(0,1),ylim=(0,1))
    fig.savefig(a.artifacts/'recorded_calibration.svg',metadata={'Date':None});plt.close(fig)
rs=d['synthetic'];fig,axes=plt.subplots(1,2,figsize=(13,7),layout='constrained')
labels=[r['profile']+' / '+r['mechanism'] for r in rs];ys=list(range(len(rs)))
for y,r in zip(ys,rs):
    axes[0].plot([r['lower'],r['upper']],[y,y],color='#4c78a8');axes[0].plot(r['mean_utility_gain'],y,'o',color='#4c78a8')
axes[0].set_yticks(ys,labels,fontsize=8);axes[0].axvline(0,color='black',lw=.7);axes[0].set_xlabel('Utility gain; paired world-bootstrap 95% MC interval')
axes[1].plot([r['mean_proxy_loss'] for r in rs],ys,'o',color='#e45756');axes[1].set_yticks(ys,[]);axes[1].axvline(0,color='black',lw=.7);axes[1].set_xlabel('Mean preference-proxy loss under frozen strategy')
fig.suptitle('Wholly synthetic generalization • exploratory, eight worlds per condition')
fig.savefig(a.artifacts/'synthetic_generalization.svg',metadata={'Date':None});plt.close(fig)
print('Scientific SVG figures rendered from aggregate plot data')
import hashlib
# Normalize harmless renderer whitespace for clean, portable Git diffs.
for svg in a.artifacts.glob('*.svg'):
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
plot_manifest={'version':'benchmark-plots-1','matplotlib':matplotlib.__version__,
    'input_plot_data_sha256':hashlib.sha256((a.artifacts/'plot_data.json').read_bytes()).hexdigest(),
    'plot_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'figures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.artifacts.glob('*.svg'))}}
(a.artifacts/'plot_manifest.json').write_text(json.dumps(plot_manifest,indent=2,sort_keys=True)+'\n')
