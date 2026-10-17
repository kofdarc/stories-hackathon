"""Build self-contained notebook. Embeds source code, never transaction data or outputs."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
cells=[]
def md(s): cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(keepends=True)})
def code(s): cells.append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':s.splitlines(keepends=True)})
md('''# Stories Coffee: the interactive decision notebook

**Open in Google Colab → Run all → confirm authorization → upload the transaction CSV.** No repository checkout, API key or private data download is required. The model runs on your uploaded file. Only aggregates and editable assumptions enter the optional reports; the delivered notebook has no data or executed outputs.

This notebook answers: *what would have to be true for this decision to beat doing nothing?* It covers opening hours, permanent branch closure, restocking/preparation, expiry markdowns, loyalty, prices, item discounts, two-item combos and delivery. Financial arithmetic is deterministic Python. Positive modeled value means **candidate for a controlled test**, not proven benefit.

The EECE490 brief asks for business actions, alternative explanations, costs, missing evidence, baselines and out-of-sample checks. It prohibits requesting clarification. We use the brief, repository evidence and explicit assumptions; no course-slide alignment is claimed.

**Privacy:** Upload only a CSV you are authorized to process in your Google/Colab environment. Replacement transaction IDs do not make customer records public. Do not share a runtime, input file or executed notebook containing private outputs. Use *Edit → Clear all outputs* before sharing; inspect any downloaded report before redistribution. The notebook makes no LLM calls and sends no data to a model API. Colab itself is a hosted environment.
''')
code(r'''# Run once. Colab provides Python and a browser widget front-end.
%pip -q install "pandas>=2.2,<4" "numpy>=1.26,<3" "matplotlib>=3.8,<4" "ipywidgets>=8,<9"
import io, json, zipfile, hashlib, html
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import ipywidgets as W
from IPython.display import display, Markdown, clear_output, HTML
try:
    from google.colab import files, output
    output.enable_custom_widget_manager()
    IN_COLAB = True
except ImportError:
    IN_COLAB = False
print("Setup ready. Run all remaining cells, then use the upload panel at the bottom.")
''')
md('''## What is measured, assumed and unidentified

The repository source inspected during development has **51,177 lines, 33,887 baskets, three branches, January 1–June 30, 2026**, with 132 exact repeated rows. About 36.45% of baskets lack a customer ID. There are only Dine-in and Takeaway orders. These are source-specific reference checks, not required totals for your upload; the audit below recomputes them.

**Measured from your upload:** sales, recorded gross profit (GP), product costs and prices, concessions, basket contents, selling-hour support, known customer histories. GP is revenue less the recorded product cost; it excludes unrecorded labor, occupancy, waste and delivery expenses. Recorded unit costs may contain allocation rules and require invoice reconciliation before treating them as avoidable cash.

**Editable assumptions:** staffing/utilities saved, actual operating hours, extension demand, permanent-closure fixed/exit costs, migration and spare capacity, inventory and shelf life, demand lost to stockouts, elasticity, marketing response, true delivery demand and costs, loyalty causality. Zero defaults mean *no benefit/cost credited*, not evidence that the input is zero. Some controls are initialized to labeled sales proxies, never observed inventory or logistics data.

All nine scenarios use the same selected horizon, normally 30 days, and calibration window, normally the latest 56 **calendar** days. They replay average historical rates; they are not forecasts of future branch profit. Absent branch dates become zero sales, which is an exposure assumption because actual opening calendars are missing. Changes in growth, seasonality, conflict, weather, competition and customer mix can invalidate the replay. Scenarios overlap and must **not be summed**.

Exact repeats are retained by default because they may be legitimate repeated units; the duplicate checkbox permits sensitivity analysis. Conflicting transaction metadata, bad types and impossible financial fields stop loading. Half-cent revenue/GP reconciliation failures are reported and block decision calculations until repaired. No identifiers are exported.
''')
code((ROOT/'engine.py').read_text())
md('''## Reading the gates

A gate is a break-even requirement under the selected assumptions. A required share above 100% is infeasible; below 0% means the arithmetic already clears the gate at zero response. `NaN` means the denominator has no positive earning capacity or there is no relevant exposure; **it never means zero risk**. Negative per-unit economics cannot be rescued by selling more units under the same model.

- **Hours:** compare retained schedule against observed selling-hour support. Removed-hour GP is full-basket GP. Savings must be cash avoidable and obey minimum staffing/service constraints. Extending earlier or later uses assumed orders and GP/hour because there is no sales evidence outside observed support. The same-day clock is 0–24; an end of 24 means midnight.
- **Permanent closure:** remove all source GP, add only avoidable fixed cash and separate savings, subtract the entire one-time exit cost, and add capacity-capped migrated orders at destination contribution after displacement and transfer costs. Fixed-cost input includes avoidable payroll/rent; do not repeat it in other savings. Committed leases, severance, transfer spending, lost brand reach and closure duration need review. A horizon with exit cost can lose money even if recurring operations save cash. This is separate from changing hours.
- **Restock/preparation:** use historical product sales, including zero-sale days, as a censored-demand proxy. Bootstrap lead-period totals with a fixed seed, select an inventory target quantile, subtract assumed on-hand stock, and round the target up to units. Compare to the editable current order. Initial current order is a **mean-sales proxy**, not an actual purchase record. Acquisition costs of new orders count; existing on-hand is sunk. The one-cycle policy resets on-hand at every cycle and liquidates leftovers, so choose a cycle matching shelf life and procurement cadence. Multi-day carryover, supplier constraints, correlated demand and recipes require an inventory model. The economic quantile is Cu/(Cu+Co), Cu = margin + shortage penalty, Co = cost − salvage + disposal, clipping negative costs to zero; it is a guide under this simplified model.
- **Waste/expiry:** near-expiry units are already owned. Their acquisition cost cancels in the comparison. Model regular-price organic sell-through versus markdown sell-through, disposal/salvage, handling, discounts on would-have-sold units and cannibalized fresh-item GP. Probabilities and expiring quantities are assumptions. Food safety/shelf-life rules override economic results.
- **Loyalty:** count reachable identified customers, then assume extra visits, reward cost on both organic and induced visits, chain displacement and campaign expense. Additional visits are specified **over the whole horizon**. Known 30-day return is descriptive and right-censored first visits are excluded. Missing IDs and ID collection changes make it unsuitable as a causal retention benchmark.
- **Price increase:** retain current discount proportions. First lose a representative share of whole containing baskets, then lose/substitute target units in surviving baskets. Whole-basket exposure includes other items; lost-basket and lost-item rates must represent disjoint stages. Alternative GP is the contribution of the replacement unit. Holding mix fixed and representative losses are assumptions.
- **Item discount:** selected product and time window; the new discount **replaces**, rather than stacks on, historical discounts. Existing units receive the offer too. Extra units pay their costs and subtract assumed displaced product GP, lost baskets and program spending. Negative leakage means a shallower offer than the historical average, not promotional lift.
- **Combos:** one A plus one B, once per basket. Existing AB buyers receive the same discounted pair; this is leakage. Incremental B attachment to A-only baskets earns combo price less former A revenue and B cost, so the rebate on A is included. Substitution, queue losses and campaign costs also count. Additional quantities in a basket are not rebated. Co-purchase support/lift suggests candidates, not causal uplift or taste compatibility. Candidate discovery uses earlier dates and checks later support; broad candidate search remains exploratory.
- **Delivery:** no delivery orders exist in the inspected source. Use in-store basket mix only as a provisional proxy. Margin = discounted merchandise × (1−commission) + retained fee − COGS − packaging − courier. Commission is assumed on discounted merchandise only; fee input is net retained. Subtract the prior contribution of channel-switched orders plus lost store baskets and setup. Platform-funded coupons, fee commissions, taxes, refunds, travel radius and capacity need actual contracts. Timing tables do not measure delivery demand.
''')
code(r'''# User interface: every financial input is editable; no hidden response model.
DATA = QUALITY = RESULT = CONTROLS = None
UI_OUTPUT = W.Output()
UPLOAD_OUTPUT = W.Output()
PANEL = W.VBox()

LABELS = {
'branch':'Branch', 'destination':'Migration destination', 'product':'Target / combo A', 'second':'Combo B',
'horizon':'Decision horizon (days)', 'lookback':'Calibration window (days)', 'start_hour':'Offer window starts', 'end_hour':'Offer window ends (exclusive)',
'new_open':'Proposed opening hour', 'new_close':'Proposed closing hour', 'avoidable_hour_cost':'Cash saved / removed hour ($)',
'recapture':'Removed sales GP recaptured (share)', 'recapture_margin':'Recapture GP multiplier',
'extension_orders_hour':'Extra hours: orders / hour', 'extension_gp_order':'Extra hours: GP / order ($)',
'extension_hour_cost':'Extra hours: cash cost / hour ($)', 'hours_setup':'Schedule change cost ($)',
'fixed_monthly':'Branch fixed costs / 30 days ($)', 'fixed_avoidable':'Fixed cost avoidable share',
'other_saved_daily':'Other cash saved / day ($)', 'exit_cost':'One-time closure/exit cost ($)',
'migration':'Orders migrating (share)', 'destination_capacity_daily':'Destination spare orders / day',
'destination_displacement':'Migrated GP displaced (share)', 'transfer_cost_order':'Cash transfer cost / order ($)',
'on_hand':'Usable on-hand units (assumed)', 'current_order':'Current order units / cycle (proxy)',
'lead_days':'Replenishment cycle / lead days', 'service_quantile':'Target demand quantile',
'salvage':'Leftover recovery / unit ($)', 'disposal':'Disposal cost / unit ($)',
'shortage_penalty':'Shortage penalty / unit ($)', 'restock_setup':'Restock/prep change cost ($)',
'expiry_units_daily':'Near-expiry units / day', 'expiry_base_sell':'Organic expiry sell-through',
'expiry_offer_sell':'Offer expiry sell-through', 'expiry_discount':'Expiry discount share',
'expiry_cannibal_daily':'Fresh regular units displaced / day', 'handling':'Markdown handling / sold unit ($)',
'waste_setup':'Markdown program cost ($)', 'loyalty_reach':'Identified customers reached (share)',
'loyalty_extra_visits':'Extra visits / reached / horizon', 'loyalty_reward':'Reward cost / redeemed visit ($)',
'loyalty_base_visits':'Organic rewarded visits / reached', 'loyalty_displacement':'Extra visit GP displaced (share)',
'loyalty_setup':'Loyalty program cost ($)', 'price_increase':'Target price increase share',
'item_loss':'Target unit loss after basket loss', 'basket_loss':'Whole containing-basket loss share',
'substitution_share':'Lost target units substituted (share)', 'alternative_margin':'Replacement unit GP ($)',
'price_setup':'Price-test implementation cost ($)', 'item_discount':'Item offer discount share',
'discount_incremental_units_daily':'Additional discounted units / day', 'discount_substitution':'Extra units displacing items (share)',
'discount_alternative_margin':'Displaced alternative GP / unit ($)', 'discount_lost_baskets_daily':'Baskets lost to offer / day',
'discount_setup':'Discount campaign cost ($)', 'combo_discount':'Combo discount on list pair (share)',
'combo_conversion':'A-only baskets adding B (share)', 'combo_substitution':'Attachments displacing items (share)',
'combo_alternative_margin':'Displaced item GP / attachment ($)', 'combo_lost_baskets_daily':'Baskets lost to combo / day',
'combo_cost':'Combo program cost ($)', 'delivery_orders_daily':'Offer delivery orders / day',
'delivery_incremental':'Genuinely new delivery order share', 'delivery_fee':'Net delivery fee retained / order ($)',
'delivery_commission':'Commission on discounted subtotal', 'delivery_packaging':'Packaging cost / order ($)',
'delivery_courier':'Merchant courier cost / order ($)', 'delivery_discount':'Delivery merchandise discount',
'delivery_displaced_gp':'GP of displaced store order ($)', 'delivery_lost_baskets_daily':'Other store baskets lost / day',
'delivery_setup':'Delivery program setup cost ($)'}
GROUPS = {
'Scope and offer timing':['branch','destination','product','second','horizon','lookback','start_hour','end_hour'],
'Opening hours':['new_open','new_close','avoidable_hour_cost','recapture','recapture_margin','extension_orders_hour','extension_gp_order','extension_hour_cost','hours_setup'],
'Permanent closure':['fixed_monthly','fixed_avoidable','other_saved_daily','exit_cost','migration','destination_capacity_daily','destination_displacement','transfer_cost_order'],
'Restock / preparation':['on_hand','current_order','lead_days','service_quantile','salvage','disposal','shortage_penalty','restock_setup'],
'Waste / expiry markdown':['expiry_units_daily','expiry_base_sell','expiry_offer_sell','expiry_discount','expiry_cannibal_daily','handling','waste_setup'],
'Loyalty':['loyalty_reach','loyalty_extra_visits','loyalty_reward','loyalty_base_visits','loyalty_displacement','loyalty_setup'],
'Price increase':['price_increase','item_loss','basket_loss','substitution_share','alternative_margin','price_setup'],
'Discounted item':['item_discount','discount_incremental_units_daily','discount_substitution','discount_alternative_margin','discount_lost_baskets_daily','discount_setup'],
'Two-item combo':['combo_discount','combo_conversion','combo_substitution','combo_alternative_margin','combo_lost_baskets_daily','combo_cost'],
'Delivery offers':['delivery_orders_daily','delivery_incremental','delivery_fee','delivery_commission','delivery_packaging','delivery_courier','delivery_discount','delivery_displaced_gp','delivery_lost_baskets_daily','delivery_setup']}
FRACTIONS = set('recapture fixed_avoidable migration destination_displacement service_quantile expiry_base_sell expiry_offer_sell expiry_discount loyalty_reach loyalty_displacement item_loss basket_loss substitution_share item_discount discount_substitution combo_discount combo_conversion combo_substitution delivery_incremental delivery_commission delivery_discount'.split())
INTEGERS = {'horizon','lookback','lead_days','start_hour','end_hour','new_open','new_close'}

def current_parameters():
    return {k:w.value for k,w in CONTROLS.items()}

def build_dashboard():
    global CONTROLS
    p=defaults(DATA)
    t,_=scope(DATA,p['branch'],p['lookback'])
    # These two initial values are sales proxies, not measured stock or channel costs.
    p['current_order']=float(np.ceil(daily_series(t,p['product']).mean()))
    p['delivery_displaced_gp']=float(baskets(t).gp.mean())
    controls={}
    style={'description_width':'300px'}
    layout=W.Layout(width='590px')
    for key,value in p.items():
        common=dict(description=LABELS[key],style=style,layout=layout)
        if key in {'branch','destination'}:
            widget=W.Dropdown(options=sorted(DATA.branch.unique()),value=value,**common)
        elif key in {'product','second'}:
            widget=W.Dropdown(options=sorted(t['product'].unique()),value=value,**common)
        elif key in INTEGERS:
            maximum=24 if 'hour' in key or key in {'new_open','new_close'} else (730 if key=='horizon' else 36500 if key=='lookback' else 30)
            minimum=0 if maximum==24 else 1
            widget=W.BoundedIntText(value=int(value),min=minimum,max=maximum,**common)
        elif key in FRACTIONS:
            widget=W.BoundedFloatText(value=float(value),min=0,max=1,step=.01,**common)
        else:
            widget=W.BoundedFloatText(value=float(value),min=0,max=1e9,step=.1,**common)
        controls[key]=widget
    CONTROLS=controls
    def branch_changed(change):
        branch=change['new'];t,_=scope(DATA,branch,int(controls['lookback'].value))
        opts=sorted(t['product'].unique())
        for key in ['product','second']: controls[key].options=opts
        if len(opts)>1 and controls['product'].value==controls['second'].value:
            controls['second'].value=next(v for v in opts if v!=controls['product'].value)
        destinations=[v for v in sorted(DATA.branch.unique()) if v!=branch]
        controls['destination'].value=destinations[0] if destinations else branch
        controls['delivery_displaced_gp'].value=float(baskets(t).gp.mean())
    controls['branch'].observe(branch_changed,names='value')
    sections=[]
    for label,keys in GROUPS.items():
        sections.append(W.VBox([controls[k] for k in keys]))
    accord=W.Accordion(children=sections,selected_index=0)
    for i,label in enumerate(GROUPS): accord.set_title(i,label)
    run=W.Button(description='Recalculate all scenarios',button_style='primary',layout=W.Layout(width='240px'))
    explore=W.Button(description='Find combo branch/time candidates',layout=W.Layout(width='290px'))
    sensitivity_button=W.Button(description='Draw break-even sensitivities',layout=W.Layout(width='250px'))
    download=W.Button(description='Download aggregate report ZIP',button_style='success',layout=W.Layout(width='260px'))
    run.on_click(render_results);explore.on_click(render_candidates)
    sensitivity_button.on_click(render_sensitivity);download.on_click(download_report)
    PANEL.children=[W.HTML('<b>Inputs below are assumptions unless explicitly labeled observed or sales proxy.</b><br>Rates are decimals: 0.10 = 10%. Costs in USD. Change controls, then recalculate. Shared salvage/disposal inputs affect both inventory and expiry.'),
      accord,W.HBox([run,download]),W.HBox([explore,sensitivity_button]),UI_OUTPUT]
    render_results()

def render_results(_=None):
    global RESULT
    with UI_OUTPUT:
        clear_output(wait=True)
        try:
            RESULT=evaluate(DATA,current_parameters())
        except (ValueError,KeyError) as exc:
            RESULT=None;display(Markdown('**Cannot calculate:** '+str(exc)));return
        r=RESULT;p=r['parameters']
        display(Markdown('### Scenario ranking: incremental USD versus doing nothing\nHistorical rates × selected horizon; inventory uses an editable current-policy baseline. **Assumptions determine the ranking; these are not measured intervention returns.**'))
        display(r['ranking'][['scenario','delta_usd','decision','gate']].round(3))
        fig,ax=plt.subplots(figsize=(10,4.7))
        table=r['ranking'].iloc[::-1]
        bars=ax.barh(table.scenario,table.delta_usd,color=['#2a9d8f' if v>0 else '#e76f51' if v<0 else '#888888' for v in table.delta_usd])
        ax.bar_label(bars,labels=[f'${v:,.0f}' for v in table.delta_usd],padding=3,fontsize=8);ax.margins(x=.16)
        ax.axvline(0,color='black',lw=.8);ax.set_xlabel(f'Conditional incremental contribution, USD / {p["horizon"]} days')
        ax.set_title('Separate scenarios — do not add them together');fig.tight_layout();display(fig);plt.close(fig)
        display(Markdown('### Measured calibration and checks'))
        display(pd.DataFrame([r['measured']]).round(3))
        display(pd.DataFrame([QUALITY]))
        display(Markdown('### Decision details and formulas'))
        for row in r['ranking'].to_dict('records'):
            display(Markdown(f'**{row["scenario"]}** — {row["detail"]}\n\n`{row["formula"]}`'))
        display(r['gates'])
        display(Markdown('### Preparation: forecasting baseline, validation and final test\nModels forecast sales, not latent demand. Pick the model using the penultimate 14 dates, then compare it with the mean-of-last-28-days baseline on the final 14 dates. Each prediction uses only earlier dates. Later test predictions may use earlier test observations, matching rolling daily operation; the winner is fixed before the test.'))
        inv=r['restock']
        print('Validation-selected model:',inv['chosen_model'])
        display(inv['scores'].round(3))
        if inv['scores'].empty:print('Fewer than 42 calendar days: insufficient split for backtest; mean baseline only.')
        display(inv['forecast'].assign(predicted_units=inv['forecast'].predicted_units.round(2)))
        print(f'Bootstrap lead-period proxy sales P10–P90: {inv["lead_sales_p10"]:.1f}–{inv["lead_sales_p90"]:.1f}. Not a calibrated prediction interval.')
        print(f'Target stock {inv["target"]:.0f}; order {inv["order"]:.0f}; expected leftovers/cycle {inv["expected_leftovers"]:.2f}; proxy stockout probability {inv["proxy_stockout_probability"]:.1%}.')
        series=daily_series(scope(DATA,p['branch'],int(p['lookback']))[0],p['product'])
        fig,ax=plt.subplots(figsize=(10,3));ax.plot(series.index,series.values,label='Observed sold units');ax.plot(inv['forecast'].date,inv['forecast'].predicted_units,'o--',label='7-day sales forecast')
        ax.set(ylabel='Units / calendar day',title=f'{p["branch"]}: {p["product"]}');ax.legend();fig.autofmt_xdate();fig.tight_layout();display(fig);plt.close(fig)
        display(Markdown('### Co-purchase evidence: selected branch and calibration window\nPairs are discovered on the first 70% of dates; later counts/lift check stability. Minimum five training baskets. Lift above one is association; search across pairs and small counts require caution. Quantity and exact duplicate rows cannot inflate basket-presence counts.'))
        display(r['pairs'].head(15).round(3))
        display(Markdown('### Loyalty: identified-customer descriptive evidence'))
        display(pd.DataFrame([r['loyalty']]).round(3))
        display(Markdown('### Hours and delivery timing\nRecorded GP/hour identifies exposure to closing. Delivery columns use in-store mix only. Low observed demand is not evidence that delivery or shorter hours will be profitable. Queue and capacity must be measured.'))
        timing=hourly_opportunities(DATA,p)
        display(timing.round(3))
        fig,ax=plt.subplots(figsize=(10,3));ax.bar(timing.hour,timing.observed_gp_daily,color='#457b9d');ax.set(xlabel='Hour (local transaction clock)',ylabel='Recorded GP / calendar day ($)',title='Value at risk when removing a selling hour');fig.tight_layout();display(fig);plt.close(fig)
        display(Markdown('**Next step:** find the assumptions that reverse the sign, then run a controlled pilot with service, customer and chain-contribution guardrails. Report ZIP uses the current controls and contains no transaction/customer rows.'))

def render_candidates(_=None):
    with UI_OUTPUT:
        clear_output(wait=True)
        try:
            candidates=combo_candidates(DATA,current_parameters())
            display(Markdown('### Which pair, where, when and at what price?\nExplore three train-supported pairs per branch/daypart. The table prices one A + B and deducts existing-pair rebate leakage, assumed substitution and program cost. **Queue losses are excluded here**; enter them in the selected scenario before deciding. Assumed adoption is shared across rows, not estimated from lift. Rankings are exploratory and do not correct for candidate search.'))
            if candidates.empty:print('Insufficient pair support. Increase calibration window or use a manager-specified pair.')
            else:display(candidates.round(3))
            print('Use a candidate by copying its branch, A, B and hour range into the controls, then recalculate.')
        except ValueError as exc:print(str(exc))

def render_sensitivity(_=None):
    with UI_OUTPUT:
        clear_output(wait=True)
        p=current_parameters()
        specs=[('Opening hours','avoidable_hour_cost',np.linspace(0,40,9)),
          ('Permanent closure','migration',np.linspace(0,1,9)),
          ('Restock / preparation','service_quantile',np.linspace(.1,.95,9)),
          ('Expiry markdown','expiry_offer_sell',np.linspace(0,1,9)),
          ('Loyalty','loyalty_extra_visits',np.linspace(0,2,9)),
          ('Price increase','basket_loss',np.linspace(0,.30,9)),
          ('Item discount','discount_incremental_units_daily',np.linspace(0,20,9)),
          ('Two-item combo','combo_conversion',np.linspace(0,1,9)),
          ('Delivery offer','delivery_incremental',np.linspace(0,1,9))]
        fig,axes=plt.subplots(3,3,figsize=(15,11))
        tables=[]
        try:
            for ax,(layer,key,values) in zip(axes.flat,specs):
                table=sensitivity(DATA,p,key,values,layer);table['scenario']=layer;tables.append(table)
                ax.plot(table[key],table.delta_usd,'o-',color='#2a9d8f');ax.axhline(0,color='black',lw=.7)
                ax.set_title(layer);ax.set_xlabel(LABELS[key],fontsize=8);ax.set_ylabel('Δ USD / horizon')
            fig.suptitle('One assumption changes at a time; every other input stays fixed. No probability is implied.')
            fig.tight_layout();display(fig)
            print('These ranges are stress-test choices. A flat line may mean zero exposure, no assumed units, or a binding capacity cap.')
        except ValueError as exc:print(str(exc))
        finally:plt.close(fig)

def report_archive(result,quality):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('decision_report.md',aggregate_report(result,quality))
        z.writestr('scenario_ranking.csv',result['ranking'].to_csv(index=False))
        z.writestr('assumptions.json',json.dumps(result['parameters'],indent=2))
        z.writestr('quality.json',json.dumps(quality,indent=2,default=str))
        z.writestr('forecast_validation_test.csv',result['restock']['scores'].to_csv(index=False))
        z.writestr('next_7_day_sales_forecast.csv',result['restock']['forecast'].to_csv(index=False))
        z.writestr('pair_stability.csv',result['pairs'].to_csv(index=False))
        z.writestr('closure_payback.csv',result['gates'].to_csv(index=False))
    return buf.getvalue()

def download_report(_=None):
    global RESULT
    with UI_OUTPUT:
        try:
            RESULT=evaluate(DATA,current_parameters()) # Never export stale widget results.
            blob=report_archive(RESULT,QUALITY)
            path=Path('/content/stories_decision_report.zip') if IN_COLAB else Path('stories_decision_report.zip')
            path.write_bytes(blob)
            if IN_COLAB:files.download(str(path))
            else:
                from IPython.display import FileLink
                display(FileLink(str(path)))
            print('Aggregate report ready. No raw transactions or customer/transaction IDs included. Review before sharing.')
        except ValueError as exc:print('Report blocked:',exc)
''')
md('''## Load authorized data and launch the controls

Upload the original `stories_transactions.csv` (the enriched CSV is also accepted; extra columns are ignored). Required columns are validated against the original 14-column schema. Files remain in the runtime; the notebook does not save a copy of the upload to Drive or publish anything. If you use a local Jupyter runtime, enter an authorized CSV path instead.

Use **Scope and offer timing** first, then open the decision's controls. The scope sets one branch, product A, product B and time window. The opening-hours and permanent-closure models use the full branch day; product price changes also cover the full day. Item discounts, combo eligibility and delivery mix use the offer window. Forecasts and loyalty use the selected branch's calibration window.

Set current inventory/purchases, avoidable labor/rent, destination capacity and campaign response from actual operations before interpreting recommendations. An illustrative price increase of 5%, offers of 10–20% and inventory quantile of 80% are **scenario defaults**, not learned optima. Extra visits, uplift/adoption, delivery demand, migration and cash savings start at zero. On branch changes, displaced store GP is reset to a measured branch average used as a proxy; inventory controls remain editable and should be reviewed for the new product/branch.
''')
code(r'''authorized=W.Checkbox(value=False,description='I am authorized to process this CSV in this runtime',indent=False,layout=W.Layout(width='650px'))
deduplicate=W.Checkbox(value=False,description='Remove exact repeated rows (sensitivity scenario)',indent=False,layout=W.Layout(width='650px'))
local_path=W.Text(value='',description='Local CSV path:',placeholder='For local Jupyter only; Colab users click Upload CSV',layout=W.Layout(width='650px'),style={'description_width':'110px'})
load_button=W.Button(description='Upload CSV / load local path',button_style='primary',layout=W.Layout(width='270px'))

def load_clicked(_=None):
    global DATA,QUALITY,RESULT
    with UPLOAD_OUTPUT:
        clear_output(wait=True)
        if not authorized.value:
            print('Confirm your authorization before loading data.');return
        try:
            if local_path.value.strip():
                payload=Path(local_path.value.strip()).read_bytes()
            elif IN_COLAB:
                uploaded=files.upload()
                if len(uploaded)!=1:raise ValueError('Choose exactly one CSV per load.')
                payload=next(iter(uploaded.values()))
            else:
                print('Enter a local CSV path above.');return
            data,quality=load_transactions(io.BytesIO(payload),drop_duplicates=deduplicate.value)
            quality['source_sha256']=hashlib.sha256(payload).hexdigest()
            display(pd.DataFrame([quality]))
            if quality['revenue_exceptions_over_half_cent'] or quality['gp_exceptions_over_half_cent']:
                raise ValueError('Financial reconciliation exceptions: repair source before decisions.')
            if data['product'].nunique()<2:raise ValueError('Two or more products required for the full combo dashboard.')
            DATA,QUALITY,RESULT=data,quality,None
            build_dashboard()
            print('Loaded. Controls and results are below. Re-load to apply the duplicate-policy checkbox.')
        except Exception as exc:
            DATA=QUALITY=RESULT=None;PANEL.children=[]
            print('Load failed:',str(exc))

load_button.on_click(load_clicked)
display(W.VBox([authorized,deduplicate,local_path,load_button,UPLOAD_OUTPUT]))
display(PANEL)
''')
md('''## Validation, pilot design and decisions that can reverse

The notebook's forecast selection uses rolling one-step predictions on a validation period and reports final-test error against a simple trailing mean. If the selected model loses on the final test, prefer the baseline until more data justify complexity. WAPE is undefined when actual test units sum to zero; MAE still works. Bootstrap quantities describe independent resamples of observed sales, not calibrated demand intervals. Prep units mean **finished SKU units**, not ingredient orders; recipes, yields, prep time and shelf life are absent.

Pair discovery uses train dates only to select candidates. Later pair support and lift are descriptive stability checks. They do not validate response to a combo. Customer return rates exclude first-seen dates with fewer than 30 follow-up days and count later purchase dates, not same-day repeat baskets; first-seen is not necessarily first-ever. No file field provides true customer churn, campaign response or price elasticity.

For any commercial pilot, compare with **do nothing through randomized assignment before purchase**. Include visitors who buy nothing. Record chain-wide contribution per assigned visitor/service block after rewards, delivery, staffing and waste; include all items, other branches and subsequent visits. Check substitution, pulled-forward purchases, ID capture and service delays. Randomize comparable branch/daypart blocks for capacity-sensitive offers, with washout informed by actual queue-clearance times. Cluster inference by assignment and plan for repeat customers. A branch-level test with only three branches has limited inferential power; repeated time blocks may help, but cannot substitute for a real power calculation.

Choose the minimum worthwhile contribution change, duration, sample size, spend cap, quality/food-safety/service limits and stop rules **before** starting, using actual variance and manager priorities. Forecast accuracy and association p-values cannot provide treatment-effect power. Do not commit to permanent closure from the transaction file: verify leases, labor obligations, actual avoidable cash costs, destination capacity, customer migration and brand effects, and compare reversible hour/staffing changes first.

**Alternative explanations:** lower recorded branch GP could reflect centrally assigned costs rather than bad procurement; discount redeemers may have bought more without offers; a higher identified repeat rate could arise from collecting more IDs; low sales could reflect a stockout or closed hours; higher average baskets could coexist with fewer total customers. Each can reverse an apparent recommendation.

**Verification shipped beside this notebook:** unit tests exercise basket-level loss and leakage identities, closure capacity and exit costs, expiry sunk-cost treatment, delivery migration, inventory constraints, censored-return handling, temporal forecast isolation and report privacy. A smoke runner executes the actual notebook cells with the real authorized local CSV, exercises widgets/report callbacks and checks embedded source parity. It writes only aggregate verification metadata and a sample chart; the distributed `.ipynb` remains output-free.
''')
notebook={'cells':cells,'metadata':{'colab':{'name':'Stories_Coffee_Decision_Lab.ipynb','provenance':[]},
 'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
 'language_info':{'name':'python','version':'3.11'}},'nbformat':4,'nbformat_minor':5}
# Stable cell IDs satisfy nbformat 4.5 without relying on nbformat package.
for i,c in enumerate(cells):c['id']=f'stories-{i:03d}'
(ROOT/'Stories_Coffee_Decision_Lab.ipynb').write_text(json.dumps(notebook,indent=1)+'\n')
print('Built output-free self-contained notebook:',len(cells),'cells')
