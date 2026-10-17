"""Stories Coffee management dashboard. Run: streamlit run app.py."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from src.analytics import (ROOT,load_data,baskets,summary,matched_products,
    counterfactual,associations,bundle_scenarios,validate,decomposition)
from src.deep_insights import daypart_economics,growth_bridge,category_null,attachment_cases
from src.causal_decisions import price_retention_gates,upsell_capacity_gates,procurement_quality_gates
from src.feature_effects import CATALOG,OUTCOMES,frames,controls,feature_curve,effect_matrix
from src.features import enrich,daily_panel,weather_effects,forecast_check,drink_mix_by_weather,hourly_profile

st.set_page_config(page_title='Stories Coffee | Decisions',page_icon='☕',layout='wide')
st.markdown('''<style>
.stApp {background:#faf8f4;color:#28231f} h1,h2,h3 {color:#4b3527}
[data-testid="stMetric"] {background:#efe9df;padding:18px;border-radius:8px}
</style>''',unsafe_allow_html=True)
px.defaults.template='plotly_white'
px.defaults.color_discrete_sequence=['#75543d','#b38b61','#547965','#ae664d']

@st.cache_data
def get_data(): return load_data()

@st.cache_data
def get_enriched(): return enrich(get_data())

@st.cache_data
def get_frames(): return frames(get_data())

@st.cache_data
def get_effects():
    path=ROOT/'reports'/'tables'/'feature_effects.csv'
    return pd.read_csv(path) if path.exists() else effect_matrix(get_frames())

try: full=get_data()
except (OSError,ValueError) as e:
    st.error(f'Cannot load Stories data: {e}. Place the authorized CSV at the project root.'); st.stop()

st.sidebar.title('STORIES COFFEE')
st.sidebar.caption('Historical evidence · Jan–Jun 2026')
pages=['Executive Overview','Causal Decision Chains','Deep Decision Insights','Sales & Transactions','Profitability Investigation',
       'Sales Forecast','Opportunity Simulator','Basket & Promotion Opportunities','Weather & Calendar','Feature Explorer','Evidence, Limitations & Assumptions']
page=st.sidebar.radio('Navigation',pages)
branches=st.sidebar.multiselect('Branch',sorted(full.branch.unique()),default=sorted(full.branch.unique()))
dates=st.sidebar.date_input('Date range',value=(full.date.min().date(),full.date.max().date()),
    min_value=full.date.min().date(),max_value=full.date.max().date())
categories=st.sidebar.multiselect('Category',sorted(full.category.unique()),default=sorted(full.category.unique()))
types=st.sidebar.multiselect('Order type',sorted(full.order_type.unique()),default=sorted(full.order_type.unique()))
if len(dates)!=2: st.info('Choose a start and end date.'); st.stop()
context=full[full.date.between(pd.Timestamp(dates[0]),pd.Timestamp(dates[1])) &
    full.category.isin(categories) & full.order_type.isin(types)]
x=context[context.branch.isin(branches)]
st.title(page)
st.caption(f'{dates[0]} → {dates[1]} · USD · {len(x):,} selected item lines · {x.transaction.nunique():,} baskets containing selected items')
if x.empty: st.info('No records match these filters.'); st.stop()
st.caption('Revenue and profit refer to selected items. Category basket counts overlap. Scenarios use selected Garden items and Harbour references from the same dates, categories and order types.')

def chart(d,xcol,ycol,title,kind='bar',**kwargs):
    st.markdown(f'**{title}**')
    fig=getattr(px,kind)(d,x=xcol,y=ycol,**kwargs)
    fig.update_layout(margin=dict(l=10,r=10,t=15,b=10),height=320)
    if 'margin' in ycol or 'ratio' in ycol: fig.update_yaxes(tickformat='.1%')
    st.plotly_chart(fig,width='stretch')

def metrics(d):
    r,g=d.revenue.sum(),d.gp.sum(); n=d.transaction.nunique()
    a,b,c,e=st.columns(4)
    a.metric('Revenue',f'${r:,.2f}');b.metric('Recorded gross profit',f'${g:,.2f}')
    c.metric('Gross margin',f'{g/r:.2%}' if r else 'Unavailable');e.metric('Distinct baskets',f'{n:,}')

def opportunity():
    result=counterfactual(x,context)
    if not x.branch.eq('Garden').any():
        st.info('Select Garden to inspect its matched-cost opportunity.');return None
    if result['unmatched_lines']:
        st.warning(f"{result['unmatched_lines']} selected Garden lines lack a same-scope Harbour match. The displayed opportunity covers matched items only.")
    return result

if page=='Executive Overview':
    r=opportunity()
    st.subheader('The findings—and what Stories should do')
    if r:
        st.markdown(f"**1. Garden’s cost gap looks systematic, not product-specific.** The matched-cost difference is **${r['matched_gap']:,.2f}** in the selected scope. Trace the costing formula and invoices before changing suppliers: this could be an accounting allocation, with zero cash savings.")
    if {'Matcha & Tea','Bakery'}.issubset(set(x.category)):
        cases=attachment_cases(x)
        free=cases[cases.assumed_adoption.eq(.03) & cases.assumed_rebate_rate.eq(0)].iloc[0]
        paid=cases[cases.assumed_adoption.eq(.03) & cases.assumed_rebate_rate.eq(.1)].iloc[0]
        st.markdown(f"**2. Test a bakery suggestion with matcha; don’t start with a rebate.** There are **{int(free.eligible_a_only_baskets):,}** selected matcha baskets without bakery. At an **assumed 3% incremental attachment**, a suggestion adds **${free.hypothetical_gp_before_expense:,.2f}** before costs; a blanket extra 10% bakery rebate produces **${paid.hypothetical_gp_before_expense:,.2f}**, because **{int(paid.existing_pairs):,}** existing pairs also receive it. These are scenarios requiring an experiment.")
    st.markdown('**3. Discounted baskets can look bigger without discounts causing extra purchases.** Larger baskets simply have more chances to contain a discounted line. The fixed-basket label-shuffle study reproduces the observed 10% basket-size gap. Judge promotions by incremental contribution per assigned visitor, including nonbuyers—not averages among redeemers.')
    orders=baskets(x);evening=orders[orders.hour.between(19,23)]
    if orders.gp.sum()>0:
        st.markdown(f"**4. Protect the evening business before buying more demand.** **{evening.gp.sum()/orders.gp.sum():.1%}** of selected recorded GP occurs at **19:00–23:59**. Audit queues and stockouts there. These records establish demand exposure, not understaffing or lost sales.")
    growth,bridge=growth_bridge(x)
    if len(growth)>1 and abs(bridge.gp_per_day_change.sum())>1e-8:
        share=bridge.iloc[0].gp_per_day_change/bridge.gp_per_day_change.sum()
        st.markdown(f"**5. Sales growth does not demonstrate better basket economics.** From **{growth.month.iloc[0]}** to **{growth.month.iloc[-1]}**, more baskets per calendar day account arithmetically for **{share:.1%}** of the GP/day change. GP/basket moves from **${growth.gp_per_basket.iloc[0]:.2f}** to **${growth.gp_per_basket.iloc[-1]:.2f}**. Use complete months for this comparison.")
    st.subheader('Where the recommendations could backfire')
    st.write('Higher item prices → possible whole-basket exit → lost contribution on other products. More attachment → extra service work → possible queue abandonment. Cheaper procurement → possible quality/waste changes → lost repeat demand. These are hypotheses to test, not causal effects established by the CSV.')
    complete=full[full.transaction.isin(x.transaction)]
    price_gates=price_retention_gates(complete,context)
    if not price_gates.empty and price_gates['product'].eq('Sparkling Water').any():
        water=price_gates.set_index('product').loc['Sparkling Water']
        st.markdown(f"**Pricing downside:** Sparkling Water's modeled price alignment can tolerate **{water.item_only_loss_break_even:.1%}** lost item sales if other purchases remain, but only **{water.whole_basket_loss_break_even:.2%}** lost containing baskets. A price pilot must measure both pathways.")
    capacity_gates=upsell_capacity_gates(complete)
    if not capacity_gates.empty and capacity_gates.scope.eq('Evening 19–23').any():
        peak=capacity_gates.set_index('scope').loc['Evening 19–23']
        st.markdown(f"**Upsell downside:** assuming 3% incremental attachment in the selected evening basket cohort adds **${peak.hypothetical_attachment_gp:,.2f}** before costs. Just **{peak.lost_baskets_break_even:.1f}** representative lost evening baskets erase that benefit. Neither attachment uplift nor abandonment is measured.")
    st.caption('Open Causal Decision Chains for quantified loss budgets, unresolved links, protection measures and stop rules. Selected-scope calculations respond to the sidebar.')
    st.divider()
    metrics(x)
    left,right=st.columns(2)
    with left: chart(summary(x,'branch'),'branch','margin','Recorded GP / selected-item revenue by branch')
    with right:
        if r:
            chart(pd.DataFrame({'case':['Recorded Garden','Harbour matched costs'],
                'gp':[r['baseline_gp'],r['baseline_gp']+r['matched_gap']]}),'case','gp','Actual versus hypothetical Garden GP (USD)')
    m=matched_products(context)
    if r and not m.empty:
        chart(m.head(10),'product','opportunity','Largest contributors to the selected Garden cost difference (USD)')
    st.write('Next: audit the largest dollar contributors; confirm avoidability; pilot changes with quality safeguards. Hold broad discount expansion pending a randomized visitor-level test.')

elif page=='Causal Decision Chains':
    st.write('Protect contribution, customers and service. The records establish exposure and arithmetic; downstream intervention effects are hypotheses until tested.')
    panels=st.tabs(['The causal chains','Whole-basket pricing risk','Upselling versus service load','Sourcing and quality'])
    with panels[0]:
        st.caption('Published decision chains below refer to the full January–June research. The other tabs calculate downside gates for the selected scope.')
        register=pd.read_csv(ROOT/'reports/tables/causal_chain_register.csv')
        for row in register.itertuples():
            st.subheader(row.decision)
            st.markdown(f'**Hypothesized chain:** {row.chain}')
            st.write(f'Observed evidence: {row.observed}. Unresolved links: {row.unidentified}.')
            st.write(f'Protect Stories: {row.protection}.')
            st.caption(f'Success metric: {row.metric}. Stop condition: {row.stop}.')
        st.download_button('Download causal decision brief',(ROOT/'reports/causal_decisions.md').read_text(),'stories_causal_decisions.md')
    with panels[1]:
        complete=full[full.transaction.isin(x.transaction)]
        p=price_retention_gates(complete,context)
        st.write('A higher product margin can be offset by losing its entire containing basket. These are two behavioral assumptions, not measured demand responses.')
        st.caption('Complete baskets are restored to measure other-item contribution at risk. Target prices come from Harbour in the selected date/category/order-type scope. Per-product scenarios overlap and must not be added.')
        if p.empty:st.info('Select Garden and a scope with matched Harbour prices.')
        else:
            st.dataframe(p,hide_index=True)
            product=st.selectbox('Inspect one product',p['product'].tolist())
            row=p.set_index('product').loc[product]
            a,b=st.columns(2)
            a.metric('Break-even: only the item is lost',f'{row.item_only_loss_break_even:.1%}')
            b.metric('Break-even: the complete basket is lost',f'{row.whole_basket_loss_break_even:.1%}')
            st.write(f'At unchanged purchases, price alignment adds ${row.hypothetical_uplift_before_response:,.2f}. The item currently contributes ${row.item_gp:,.2f}, while containing baskets contribute ${row.containing_basket_gp:,.2f}.')
            st.write('Require contribution per assigned eligible visitor, including nonbuyers and chain displacement. A margin increase alone is insufficient.')
    with panels[2]:
        st.write('An attachment prompt can add product contribution while reducing completed purchases if it creates service delays. Delay and abandonment are not measured in this file.')
        complete=full[full.transaction.isin(x.transaction)]
        a,b=st.columns(2)
        with a:
            adoption=st.slider('Assumed genuinely incremental attachment (%)',0,20,3)/100
            losses=st.number_input('Assumed lost complete baskets in each displayed scope',min_value=0.,value=0.,step=1.)
        with b:
            expense=st.number_input('Assumed total added operating/program expense per scope (USD)',min_value=0.,value=0.,step=10.)
            displacement=st.number_input('Assumed contribution displaced by substitution per scope (USD)',min_value=0.,value=0.,step=10.)
        gates=upsell_capacity_gates(complete,adoption,expense,losses,displacement)
        if gates.empty:st.info('The selected basket cohort needs both matcha and bakery records.')
        else:st.dataframe(gates,hide_index=True)
        st.caption('Selected baskets are restored in full. All-hours and evening rows are alternative scopes, not additive. Lost baskets are assumed representative at observed GP/basket; do not double-count substitution already included in lost baskets. Negative loss budgets mean costs already exceed modeled benefit.')
        st.write('Measure total contribution per randomized service block after incremental labor and waste, alongside waits, completions and quality. Never infer an allowable delay in seconds without arrival/service-time data.')
    with panels[3]:
        if x.branch.eq('Garden').any():st.dataframe(procurement_quality_gates(x,context),hide_index=True)
        else:st.info('Select Garden for the procurement downside gate.')
        st.write('Accounting allocation → recorded margin gap is a different mechanism from invoices → avoidable cash costs. Verify the latter before changing suppliers. A break-even volume-loss ceiling is not an acceptable quality target; Stories must set quality, reliability and service limits independently.')

elif page=='Deep Decision Insights':
    st.write('Each investigation connects an observed pattern to a management decision, a financial gate and an experiment. Metrics below follow the selected scope; scenarios remain unmeasured assumptions.')
    tabs=st.tabs(['Protect evening service','Quality of growth','Hidden attachment preferences','Complete research brief'])
    with tabs[0]:
        st.subheader('Does service coverage follow the actual demand peak?')
        o=baskets(x); evening=o[o.hour.between(19,23)];morning=o[o.hour.between(7,10)]
        a,b,c=st.columns(3)
        a.metric('Evening share of selected baskets',f'{len(evening)/len(o):.1%}')
        b.metric('Evening recorded GP',f'${evening.gp.sum():,.2f}')
        c.metric('Morning share of selected baskets',f'{len(morning)/len(o):.1%}')
        chart(daypart_economics(x),'period','baskets_per_observed_day_hour','Baskets per observed day and nominal clock-hour',color='branch',barmode='group')
        st.write('Inspect evening queues and stockouts before adding shifts. Demand concentration establishes financial exposure, not understaffing or recoverable lost sales.')
        cost=st.number_input('Assumed incremental coverage cost for selected scope (USD)',min_value=0.,value=100.,step=10.)
        if len(evening) and evening.gp.mean()>0:
            st.metric('Recovered baskets needed to cover assumed cost',f'{cost/evening.gp.mean():.1f}')
        st.caption('Break-even uses selected-item GP/basket at historical mix. Include all incremental labor, waste and service costs before deciding; no staffing costs are measured here.')
    with tabs[1]:
        st.subheader('Are we selling more baskets, or earning more from each one?')
        monthly,bridge=growth_bridge(x)
        st.dataframe(monthly,hide_index=True)
        if monthly.month.nunique()>1:
            chart(bridge,'factor','gp_per_day_change','First-to-last selected month: exact GP/day bridge (USD)')
        st.write('Rising sales do not establish better upselling or profitable promotions. The bridge separates basket frequency from GP/basket and shares their interaction equally. Fewer or partial months change the comparison.')
        st.caption('Calendar-day rates use full calendar months, so partial-date selections count unselected calendar days as outside the observed scope. Use full months for growth comparisons; weekday-standardized rates use observed dates.')
    with tabs[2]:
        st.subheader('Which pairs occur beyond a basket-size and context baseline?')
        @st.cache_data
        def contextual_pairs(data):
            a=category_null(data[data.date<'2026-05-01'])
            b=category_null(data[data.date>='2026-05-01'],seed=491)
            if a.empty or b.empty:return pd.DataFrame()
            return a.merge(b,on=['category_a','category_b'],suffixes=('_train','_replication')).sort_values('conditional_enrichment_train',ascending=False)
        p=contextual_pairs(x)
        if p.empty:st.info('Choose at least two categories and dates spanning both Jan–Apr and May–Jun for chronological comparison.')
        else:
            st.dataframe(p,hide_index=True)
            top=p.head(6).copy();top['pair']=top.category_a+' + '+top.category_b
            long=top.melt(id_vars='pair',value_vars=['conditional_enrichment_train','conditional_enrichment_replication'],var_name='period',value_name='enrichment')
            chart(long,'pair','enrichment','Observed pairs / basket-size-preserving expected pairs',color='period',barmode='group')
        st.caption('399 label shuffles within branch × month × order type × four-hour daypart preserve basket line counts and context-specific category frequencies. BH q-values cover all tested category pairs. These are exchangeability diagnostics, not causal offer effects. Both periods were inspected retrospectively.')
        if {'Matcha & Tea','Bakery'}.issubset(set(x.category)):
            st.write('Matcha-to-bakery experiment: one incremental bakery unit per adopting matcha-only basket. An extra rebate also reaches existing paired purchases; no operating expenses included.')
            st.dataframe(attachment_cases(x),hide_index=True)
        st.write('Test a no-discount prompt before paying for existing co-purchases. Measure whole-basket contribution per assigned eligible customer/order, including substitution and non-completions.')
    with tabs[3]:
        st.caption('Published research brief below covers the complete January–June file, independent of sidebar filters.')
        st.markdown((ROOT/'reports/deep_insights.md').read_text())

elif page=='Sales & Transactions':
    st.write('Reconstructed from Abel Atangs’ reference: synchronized location filtering and four charts in a two-by-two layout. Stories counts distinct baskets, since its rows are item lines.')
    metrics(x)
    a,b=st.columns(2)
    with a:
        chart(summary(x,'month'),'month','revenue','Sum of revenue by month (USD)','line',markers=True)
        chart(summary(x,'hour'),'hour','transactions','Distinct baskets by hour of day')
    with b:
        d=summary(x,'weekday').sort_values('weekday');d['day']=d.weekday.map(dict(enumerate(['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])))
        chart(d,'day','transactions','Distinct baskets by weekday')
        d=summary(x,'category').sort_values('transactions')
        chart(d,'transactions','category','Most popular categories: baskets containing category',orientation='h')
    st.dataframe(summary(x,'branch'),hide_index=True)
    st.dataframe(summary(x,'order_type'),hide_index=True)
    st.dataframe(summary(x,'product').sort_values('gp',ascending=False),hide_index=True)
    # Customer aggregates use complete selected baskets, with no identifiers shown.
    o=baskets(full[full.transaction.isin(x.transaction)])
    known=o.dropna(subset=['customer']);visits=known.groupby('customer').size()
    st.caption(f'Customer IDs missing on {o.customer.isna().mean():.1%} of selected baskets. Among {len(visits):,} identified customers, {visits.gt(1).mean():.1%} have repeat baskets within scope. Identification bias prevents generalization.')

elif page=='Profitability Investigation':
    metrics(x); r=opportunity()
    chart(summary(x,'branch'),'branch','margin','Branch gross margin: GP / revenue')
    m=matched_products(context)
    if not m.empty:
        chart(m,'cost_Harbour','cost_Garden','Same-product recorded unit cost (USD)','scatter',hover_name='product')
        chart(m,'product','cost_ratio','Garden / Harbour recorded cost ratio: identical products')
        st.dataframe(m,hide_index=True)
        if r:
            monthly=pd.DataFrame([dict(month=k,**counterfactual(g,context)) for k,g in x.groupby('month')])
            chart(monthly,'month','matched_gap','Monthly Garden matched-cost difference (USD)')
    chart(summary(x,'branch'),'branch','gp_per_transaction','Recorded GP per basket containing selected items (USD)')
    disc=x.groupby('branch').agg(lines=('discount','size'),discounted_lines=('discounted','sum'),
        mechanical_concession=('concession','sum'),mean_line_discount=('discount','mean'))
    disc['discounted_line_share']=disc.discounted_lines/disc.lines
    st.dataframe(disc)
    st.caption('Matched comparisons use Garden and Harbour within the same selected time/category/order-type scope, even if Harbour is hidden by the branch filter.')
    if set(context.branch)==set(full.branch) and context.groupby('branch')["product"].nunique().nunique()==1:
        try: st.dataframe(decomposition(context),hide_index=True)
        except ValueError as e: st.info(str(e))
    st.write('Shapley attribution is GP per unit, averaged across all factor orderings; it assigns interactions once. It does not establish causation.')

elif page=='Sales Forecast':
    tables=ROOT/'reports'/'tables'
    if not (tables/'forecast_daily.csv').exists():
        st.info('Run scripts/forecast.py to fit the models and write the forecast tables.'); st.stop()
    f=pd.read_csv(tables/'forecast_daily.csv',parse_dates=['date'])
    q=pd.read_csv(tables/'forecast_intervals.csv').set_index(['target','grain'])
    sc=pd.read_csv(tables/'forecast_scores.csv')
    target=st.radio('Measure',['revenue','gp','baskets'],horizontal=True,format_func={'revenue':'Revenue','gp':'Gross profit','baskets':'Baskets'}.get)
    sel=branches or sorted(full.branch.unique())
    f=f[(f.target==target)&f.branch.isin(sel)]
    hist=full[full.branch.isin(sel)].groupby('date').agg(revenue=('revenue','sum'),gp=('gp','sum'),baskets=('transaction','nunique'))[target]
    june=hist[hist.index>='2026-06-01'].mean(); fm=f.assign(month=f.date.dt.strftime('%Y-%m')).groupby('month').forecast.sum()
    unit='' if target=='baskets' else '$'
    a,b,c=st.columns(3)
    a.metric('June actual per day',f'{unit}{june:,.0f}')
    for col,(mo,v) in zip([b,c],fm.items()): col.metric(f'{mo} forecast',f'{unit}{v:,.0f}',f'{v/f[f.date.dt.strftime("%Y-%m")==mo].date.nunique()/june-1:+.1%} per day vs June')
    both=pd.concat([hist.rename('value').reset_index().assign(kind='Actual'),
                    f.groupby('date').forecast.sum().rename('value').reset_index().assign(kind='Forecast')])
    w=(both.assign(week=both.date.dt.to_period('W-SUN').dt.start_time).groupby(['week','kind'])
       .agg(per_day=('value','mean'),days=('date','nunique')).reset_index().query('days==7'))
    lo,hi=q.loc[(target,'week'),['q10','q90']]
    fw=w[w.kind=='Forecast']
    fig=px.line(w,x='week',y='per_day',color='kind',markers=True,labels={'per_day':'Per day, weekly average','week':'Week'})
    fig.add_scatter(x=list(fw.week)+list(fw.week[::-1]),y=list(fw.per_day*hi)+list(fw.per_day[::-1]*lo),fill='toself',
                    line=dict(width=0),fillcolor='rgba(84,121,101,.18)',name='80% interval',hoverinfo='skip')
    fig.update_layout(height=380,margin=dict(l=10,r=10,t=15,b=10))
    st.plotly_chart(fig,width='stretch')
    st.caption(f'Full weeks only. Models are fitted on all Jan–Jun history and categories; only the branch filter applies. Band from chain-wide weekly backtest errors of {f.model.iloc[0]}.')
    st.markdown('**Monthly forecast by branch**')
    st.dataframe(f.assign(month=f.date.dt.strftime('%Y-%m')).pivot_table(index='branch',columns='month',values='forecast',aggfunc='sum').round(0))
    st.markdown('**Backtest: 7 rolling origins, 28-day horizon** (WAPE = total absolute error / total actual)')
    st.dataframe(sc[sc.target==target].drop(columns='target').style.format({'mae':'{:.2f}','wape':'{:.1%}','bias':'{:+.1%}','weekly_wape':'{:.1%}','skill_vs_naive':'{:+.1%}'}),hide_index=True)
    with st.expander('Full forecasting report'):
        path=ROOT/'reports'/'forecasting.md'
        st.markdown(path.read_text().replace('![Revenue forecast](figures/forecast.png)','') if path.exists() else 'Run scripts/forecast.py.')

elif page=='Opportunity Simulator':
    r=opportunity()
    if r:
        st.warning('Scenario replay of selected historical Garden items. Assumptions are editable; results are not forecasts or observed savings.')
        a,b=st.columns(2)
        with a:
            recovery=st.slider('Recoverable recorded cost difference (%)',0,100,50)/100
            coverage=st.slider('Proportional portfolio coverage (%)',0,100,100)/100
            price=st.slider('Price adjustment (%)',-20,30,0)/100
        with b:
            loss=st.slider('Assumed proportional demand loss (%)',0,50,0)/100
            expense=st.number_input('Pilot implementation expense (USD; assumed)',min_value=0.,value=0.,step=100.)
        s=counterfactual(x,context,recovery,coverage,price,loss,expense)
        a,b,c=st.columns(3);a.metric('Scenario revenue',f"${s['revenue']:,.2f}")
        b.metric('Scenario gross profit',f"${s['gp']:,.2f}");c.metric('Net benefit after expense',f"${s['net_benefit']:,.2f}")
        st.write(f"Baseline Garden GP: ${s['baseline_gp']:,.2f}. Break-even proportional volume loss: {s['break_even_demand_loss']:.2%}. A negative threshold means the scenario loses money even without volume loss.")
        st.caption('Coverage scales the dollar cost difference uniformly, rather than selecting a count of products. Volume loss scales both revenue and variable cost; product mix and discounts stay fixed. Expense is subtracted once. No cash-cost interpretation is assured.')
        st.download_button('Download scenario assumptions and results',pd.DataFrame([dict(recovery=recovery,coverage=coverage,price_change=price,demand_loss=loss,expense=expense,**s)]).to_csv(index=False),'stories_scenario.csv')

elif page=='Basket & Promotion Opportunities':
    complete=full[full.transaction.isin(x.transaction)]
    st.caption('Basket metrics restore all items in baskets containing the selected items, preserving basket economics after category filtering. Association eligibility follows this basket scope.')
    o=baskets(complete); a,b,c=st.columns(3)
    a.metric('Mean units / complete basket',f'{o.units.mean():.2f}')
    b.metric('Mean GP / complete basket',f'${o.gp.mean():.2f}');c.metric('Discount-exposed baskets',f'{o.discounted.mean():.1%}')
    chart(o.groupby('products').size().rename('baskets').reset_index(),'products','baskets','Distinct products per complete basket')
    st.dataframe(o.groupby(['branch','order_type','discounted']).agg(baskets=('gp','size'),mean_gp=('gp','mean'),mean_units=('units','mean'),mean_revenue=('revenue','mean')).reset_index(),hide_index=True)
    pairs=associations(complete)
    st.write('Product pairs: train Jan–Apr (minimum 30 baskets); holdout May–Jun. Associations are exploratory and cannot prove cross-sell response.')
    if pairs.empty: st.info('No pair meets training support in this scope. No bundle is recommended from these records.')
    else:
        st.dataframe(pairs,hide_index=True)
        st.write('Illustrative 2% / 5% / 10% incremental adoption, with a 10% attached-product rebate also paid on existing pairs. No program expenses included.')
        st.dataframe(bundle_scenarios(complete,pairs),hide_index=True)
    d=complete.groupby('discount').agg(lines=('discount','size'),concessions=('concession','sum'),revenue=('revenue','sum'),gp=('gp','sum'),list_value=('list_value','sum'))
    d['gp_without_concession']=d.gp+d.concessions
    d['required_incremental_volume']=d.concessions/d.gp.replace(0,float('nan'))
    st.dataframe(d)
    st.caption('Required volume = concession / observed discounted GP at constant mix, ignoring expenses. Concessions are list-price arithmetic, not recoverable savings. Any-discount basket exposure can select larger baskets mechanically.')
    with st.expander('Existing controlled descriptive discount investigation'):
        st.markdown((ROOT/'analysis/outputs/BUSINESS_RECOMMENDATION.md').read_text())

elif page=='Weather & Calendar':
    try: e=get_enriched()
    except (OSError,ValueError) as err:
        st.error(f'External data unavailable: {err}. Run scripts/fetch_external.py.'); st.stop()
    e=e[e.index.isin(x.index)]
    st.subheader('Demand follows the clock, not the weather')
    st.write('Beirut weather (Open-Meteo ERA5) and the Lebanese calendar are joined by date and transaction hour. One Beirut point is assumed for all branches; lunar holidays are estimates.')
    p=daily_panel(e)
    a,b,c=st.columns(3)
    a.metric('Rainy days (≥1 mm)',f"{p.groupby('date').rainy.first().sum()}")
    b.metric('Public-holiday days',f"{p.groupby('date').holiday.first().sum()}")
    c.metric('Mean temperature',f"{p.groupby('date').temp_mean.first().mean():.1f}°C")
    daily=p.groupby('date').agg(baskets=('baskets','sum'),temp_mean=('temp_mean','first'),rainy=('rainy','first')).reset_index()
    left,right=st.columns(2)
    with left: chart(daily,'temp_mean','baskets','Daily baskets vs mean temperature (°C)','scatter',color='rainy')
    with right:
        mix=drink_mix_by_weather(e)
        if not mix.empty: chart(mix,'temp_band','cold_share','Cold share of hot + cold drink units by temperature band')
    if p.date.nunique()>=60 and p.weekday.nunique()==7:
        st.markdown('**Association with daily baskets, controlling for branch × weekday and trend**')
        eff=weather_effects(p)
        fig=px.scatter(eff,x='effect',y='feature',error_x=eff.ci_high-eff.effect,error_x_minus=eff.effect-eff.ci_low)
        fig.add_vline(x=0,line_dash='dot');fig.update_xaxes(tickformat='.0%');fig.update_layout(height=320,margin=dict(l=10,r=10,t=15,b=10))
        st.plotly_chart(fig,width='stretch')
        st.caption('95% intervals use week-clustered standard errors. These are associations, not causal effects.')
        if p.date.min()<pd.Timestamp('2026-05-01')<=p.date.max(): st.dataframe(forecast_check(p),hide_index=True)
    else: st.info('Select at least 60 days to estimate effects.')
    st.markdown('**The clock, not the weather: hourly dine-in and cold-drink shares**')
    hp=hourly_profile(x).melt(id_vars=['hour','baskets'],var_name='measure',value_name='share')
    fig=px.line(hp,x='hour',y='share',color='measure',markers=True)
    fig.update_yaxes(tickformat='.0%');fig.update_layout(height=320,margin=dict(l=10,r=10,t=15,b=10))
    st.plotly_chart(fig,width='stretch')
    st.caption('Dine-in steps at 18:00 and cold share at 11:00 and 19:00, identically in every month and branch.')
    check=ROOT/'reports'/'tables'/'clock_template_check.csv'
    if check.exists(): st.dataframe(pd.read_csv(check),hide_index=True)
    with st.expander('Feature-loop log and conclusion'):
        path=ROOT/'reports'/'feature_loop.md'
        st.markdown(path.read_text() if path.exists() else 'Run scripts/run_analysis.py to generate the report.')
    with st.expander('Full external-factor report'):
        path=ROOT/'reports'/'external_factors.md'
        st.markdown(path.read_text() if path.exists() else 'Run scripts/run_analysis.py to generate the report.')

elif page=='Feature Explorer':
    st.subheader('Every engineered feature and its effect')
    st.write('This page covers the whole file; the sidebar filters do not apply. Each feature is tested against each outcome twice. **Raw** uses no adjustment. **Controlled** compares only within the same branch, month, clock hour (and weekday for demand) and promotion window. An effect is **replicated** when it is significant after a false-discovery correction and holds in both Jan–Mar and Apr–Jun. These are associations, not proof of cause.')
    m=get_effects()
    verdicts=['Replicated effect','Unreplicated (one half only)','Confounded (raw only)','No effect','Mechanical or selection','Absorbed by controls']
    colors=dict(zip(verdicts,['#547965','#b38b61','#ae664d','#d8cfc2','#9a9a9a','#e9e4dc']))
    a,b,c,d=st.columns(4)
    a.metric('Features',f"{m.base_feature.nunique()}");b.metric('Feature × outcome tests',f'{len(m):,}')
    c.metric('Replicated effects',f"{m.verdict.eq('Replicated effect').sum()}");d.metric('Confounded (raw only)',f"{m.verdict.eq('Confounded (raw only)').sum()}")
    v=m.groupby(['group','verdict']).size().rename('tests').reset_index()
    fig=px.bar(v,y='group',x='tests',color='verdict',orientation='h',category_orders={'verdict':verdicts},color_discrete_map=colors)
    fig.update_layout(height=340,margin=dict(l=10,r=10,t=15,b=10),legend_title_text='')
    st.markdown('**Verdicts by feature group**');st.plotly_chart(fig,width='stretch')
    st.caption('Only the clock (hour, daypart, weekday) and the payday window hold up. Weather, air quality, holidays and customer history do not. "Confounded" effects look real without controls but vanish once branch, season and hour are fixed.')

    groups=st.multiselect('Feature groups',sorted(m.group.unique()),default=sorted(m.group.unique()))
    shown=m[m.group.isin(groups)]
    heat=shown.assign(signal=shown.t.clip(-10,10).where(~shown.verdict.isin(['Mechanical or selection','Absorbed by controls'])))
    grid=heat.pivot_table(index='feature',columns='outcome',values='signal',aggfunc='first').reindex(columns=[o for o in OUTCOMES if o in heat.outcome.unique()])
    order=heat.groupby('feature').signal.apply(lambda s:s.abs().max()).sort_values(ascending=False).index
    grid=grid.reindex(order)
    fig=px.imshow(grid,color_continuous_scale=['#ae664d','#f4efe8','#547965'],zmin=-10,zmax=10,aspect='auto',
                  labels=dict(color='controlled t'))
    fig.update_layout(height=max(400,16*len(grid)),margin=dict(l=10,r=10,t=15,b=10))
    st.markdown('**Controlled signal for every feature × outcome** (t-statistic, capped at ±10; |t| < 2 is noise; grey cells are definitional or untestable)')
    st.plotly_chart(fig,width='stretch')

    st.markdown('**All results**')
    f1,f2=st.columns(2)
    pick_v=f1.multiselect('Verdict',verdicts,default=verdicts[:3])
    pick_o=f2.multiselect('Outcome',list(OUTCOMES),default=list(OUTCOMES),format_func=lambda o:OUTCOMES[o][1])
    table=shown[shown.verdict.isin(pick_v)&shown.outcome.isin(pick_o)].sort_values('q')
    st.dataframe(table[['feature','group','outcome_label','contrast','raw_effect','effect','ci_low','ci_high','unit','q','replicates','verdict','controls','n','description']],
        hide_index=True,column_config={c:st.column_config.NumberColumn(format='%.2f') for c in ['raw_effect','effect','ci_low','ci_high']}|{'q':st.column_config.NumberColumn(format='%.4f')})
    st.download_button('Download all results (CSV)',m.to_csv(index=False),'stories_feature_effects.csv')

    st.markdown('**Drill into one feature**')
    fr=get_frames()
    d1,d2=st.columns(2)
    feature=d1.selectbox('Feature',list(CATALOG),index=list(CATALOG).index('rainy'),format_func=lambda f:f'{f} — {CATALOG[f][2]}')
    valid=[o for o in m[m.base_feature.eq(feature)].outcome.unique()]
    outcome=d2.selectbox('Outcome',valid,format_func=lambda o:OUTCOMES[o][1])
    frame=fr['daily'] if outcome=='daily_baskets' else fr['hourly'] if outcome=='hourly_baskets' else fr['basket']
    curve=feature_curve(frame,feature,outcome,controls(feature,outcome))
    fig=px.line(curve.melt(id_vars=['level','n'],value_vars=['raw','controlled'],var_name='view',value_name=outcome),
                x='level',y=outcome,color='view',markers=True,hover_data=['n'],color_discrete_map={'raw':'#ae664d','controlled':'#547965'})
    fig.update_layout(height=340,margin=dict(l=10,r=10,t=15,b=10),xaxis_title=feature,yaxis_title=OUTCOMES[outcome][1])
    st.plotly_chart(fig,width='stretch')
    for _,r in m[m.base_feature.eq(feature)&m.outcome.eq(outcome)].iterrows():
        st.write(f"**{r.feature}** ({r.contrast}): raw {r.raw_effect:+.2f} {r.unit} → controlled {r.effect:+.2f} {r.unit} "
                 f"(95% CI {r.ci_low:+.2f} to {r.ci_high:+.2f}; q = {r.q:.3g}). Verdict: **{r.verdict}**.")
    st.caption(f"Controls: {' × '.join(controls(feature,outcome))}. The controlled line shows the outcome after removing those differences. If the raw line slopes and the controlled line is flat, the feature was only standing in for season, branch or time of day.")

else:
    st.write('Source quality below covers the entire file; business charts elsewhere follow selected scope.')
    st.json(validate(full))
    for name,label in [('assumptions_and_limitations.md','Hypotheses and assumptions'),('methodology.md','Methodology'),
                       ('experiment_plan.md','Proposed experiments'),('reference_implementation.md','Reference audit and attribution')]:
        with st.expander(label): st.markdown((ROOT/'reports'/name).read_text())

st.divider()
st.caption('Stories Coffee · observed records, explicit assumptions, untested interventions. Reference concepts: Abel Atangs / coffee-shop-analytics. All Stories calculations and interface code are original.')
