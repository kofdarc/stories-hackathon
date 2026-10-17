"""Python-generated charts from the same aggregates as the recommendation text."""
import base64
from io import BytesIO
import os
import textwrap
import threading

os.environ.setdefault('MPLCONFIGDIR','/tmp/stories-matplotlib')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
import pandas as pd

LOCK=threading.Lock()
GREEN='#315c48'; GOLD='#b28c50'; GREY='#e0e4d9'; INK='#344136'


def image(figure,title,caption):
    stream=BytesIO()
    FigureCanvasAgg(figure).print_png(stream)
    return dict(src='data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode(),
                alt=title,title=title,caption=caption)


def axis(title,height=3.5):
    fig=Figure(figsize=(9,height),dpi=110,layout='constrained',facecolor='#fffefa')
    ax=fig.subplots();ax.set_facecolor('#fffefa')
    ax.set_title(title,loc='left',fontsize=12,pad=16,color=INK,fontweight='medium')
    ax.tick_params(colors=INK,labelsize=9,length=0,pad=8)
    for spine in ax.spines.values():spine.set_visible(False)
    ax.set_axisbelow(True)
    return fig,ax


def bars(title,labels,values,xlabel,caption):
    fig,ax=axis(title,max(2.8,.43*len(labels)+1.4))
    if not labels:
        ax.text(.5,.5,'Not enough observations for this chart',ha='center',transform=ax.transAxes,color=INK)
        ax.set_xticks([]);ax.set_yticks([])
    else:
        labels=['\n'.join(textwrap.wrap(v,36)) for v in labels]
        ax.barh(labels,values,color=GREEN,height=.6);ax.invert_yaxis();ax.grid(axis='x',color=GREY,alpha=.65)
        ax.set_xlabel(xlabel,fontsize=9,color=INK,labelpad=10)
        spread=max([abs(v) for v in values] or [1]) or 1
        ax.margins(x=.17)
        for i,v in enumerate(values):ax.text(v+spread*.02,i,f'{v:,.1f}',va='center',fontsize=9,color=INK)
    return image(fig,title,caption)


def attach_charts(x,report):
    """One chart per layer; observed patterns and price scenarios stay distinct."""
    with LOCK:
        last=x.date.max();start=max(x.date.min(),last-pd.Timedelta(days=55));days=(last-start).days+1
        recent=x[x.date.ge(start)]
        cards={c['key']:c for c in report['cards']}
        fig,ax=axis('Profit by hour and branch')
        for branch,g in recent.groupby('branch'):
            profile=(g.groupby('hour').gp.sum()/days).reindex(range(24),fill_value=0)
            active=range(int(recent.hour.min()),int(recent.hour.max())+1)
            ax.plot(list(active),profile.loc[list(active)],marker='o',markersize=3,linewidth=2,label=str(branch))
        ax.set_xlabel('Hour of day',fontsize=9,color=INK);ax.set_ylabel('Gross profit per calendar day ($)',fontsize=9,color=INK)
        ax.grid(axis='y',color=GREY);ax.legend(frameon=False,fontsize=9)
        cards['hours']['chart']=image(fig,'Profit by hour and branch',f'Observed averages over the latest {days} days in your CSV. Before payroll and rent; not an optimal schedule.')
        branch=x.groupby('branch').gp.sum()/((x.date.max()-x.date.min()).days+1)
        cards['closure']['chart']=bars('Branch gross profit before operating costs',list(branch.index),branch.tolist(),
            'Gross profit per calendar day ($)','Lower gross profit identifies a review priority. It does not show which branch should close.')
        rows=cards['restock']['table'][:12]
        cards['restock']['chart']=bars('Recent daily sales to plan preparation around',
            [r['branch']+' · '+r['item'] for r in rows],[float(r['daily_units']) for r in rows],
            'Average units sold per calendar day','Sales guide only. Subtract stock on hand and check delivery lead times, shelf life and stockouts before ordering.')
        rows=cards['waste']['table'][:5]
        cards['waste']['chart']=bars('Fresh items to check for smaller batches',
            [r['branch']+' · '+r['item'] for r in rows],[float(r['daily_units']) for r in rows],
            'Average units sold per calendar day','These are slower-selling fresh-category items. The CSV does not measure discarded stock or waste savings.')
        fig,ax=axis('How sales changes can make a price change pay')
        revenue=float(recent.revenue.sum());cost=float(recent.line_cost.sum());old=revenue-cost
        volume=np.linspace(-.25,.3,150)
        for change,color,label in [(0.05,GREEN,'Prices +5%'),(-.05,GOLD,'Prices −5%')]:
            delta=(revenue*(1+change)-cost)*(1+volume)-old
            values=delta/old*100 if old>0 else delta
            ax.plot(volume*100,values,color=color,linewidth=2.5,label=label)
        ax.axhline(0,color=INK,linewidth=.8);ax.axvline(0,color=GREY,linewidth=.8)
        ax.set_xlabel('Change in volume sold (%)',fontsize=9,color=INK)
        ax.set_ylabel('Change in gross profit (%)' if old>0 else 'Change in gross profit ($)',fontsize=9,color=INK)
        ax.grid(axis='y',color=GREY);ax.legend(frameon=False,fontsize=9)
        cards['pricing']['chart']=image(fig,'Price and sales-volume scenarios',
            'All branches combined, latest history. Assumes unchanged product mix, discounts and unit costs. The sales response is unknown; these are scenarios, not forecasts.')
        rows=cards['combos']['table'][:4]
        fig,ax=axis('Pairs seen in both earlier and later sales',max(3,.8*len(rows)+1.4))
        if rows:
            positions=np.arange(len(rows));labels=[r['branch']+' · '+r['when']+'\n'+'\n'.join(textwrap.wrap(r['items'],46)) for r in rows]
            ax.barh(positions-.17,[r['earlier'] for r in rows],height=.3,color=GREEN,label='Earlier period (70% of dates)')
            ax.barh(positions+.17,[r['later'] for r in rows],height=.3,color=GOLD,label='Later period (30% of dates)')
            ax.set_yticks(positions,labels);ax.invert_yaxis();ax.set_xlabel('Baskets containing both items',fontsize=9,color=INK)
            ax.legend(frameon=False,fontsize=8,loc='lower right');ax.grid(axis='x',color=GREY)
        else:
            ax.text(.5,.5,'No pair meets the earlier/later observation threshold',ha='center',transform=ax.transAxes,fontsize=10)
            ax.set_xticks([]);ax.set_yticks([])
        cards['combos']['chart']=image(fig,'Pairs seen in both earlier and later sales',
            'Periods have different lengths. These counts show repeat co-purchases, not extra demand caused by an offer. Start with a small full-price pairing test.')
    return report
