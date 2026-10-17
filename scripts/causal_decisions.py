"""Build evidence-linked causal hypotheses and business-protection thresholds."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.analytics import ROOT,load_data,baskets,counterfactual
from src.causal_decisions import price_retention_gates,upsell_capacity_gates,procurement_quality_gates

def run(source=ROOT/'stories_transactions.csv',out=ROOT/'reports'):
    x=load_data(source);out=Path(out);tables=out/'tables';tables.mkdir(parents=True,exist_ok=True)
    price=price_retention_gates(x,x);capacity=upsell_capacity_gates(x);quality=procurement_quality_gates(x,x)
    price.to_csv(tables/'price_basket_retention_gates.csv',index=False)
    capacity.to_csv(tables/'upsell_capacity_gates.csv',index=False)
    quality.to_csv(tables/'procurement_quality_gates.csv',index=False)
    chains=[
      dict(decision='Garden costing',chain='Branch cost rule → lower recorded GP → pressure to change sourcing → possible quality/supply change → customer retention → chain contribution',
           observed='Fixed product-branch costs and matched gap; rule origin unknown',
           unidentified='Cash avoidability; recipe/quality response; repeat demand',
           protection='Audit invoices and allocations first; change sourcing only after cash cost and quality validation',
           metric='Avoidable invoice cost per conforming unit; contribution after all incremental costs',
           stop='Accounting-only gap, failed quality specifications or contribution below the pre-agreed gate'),
      dict(decision='Product pricing',chain='List price increase → higher contribution per retained item → item substitution OR whole-basket exit → lost contribution on other products → net chain GP',
           observed='Prices, item GP and complete affected-basket GP',unidentified='Demand elasticity, basket abandonment, branch switching',
           protection='Measure the complete basket and chain-wide displacement; do not use item margin alone',
           metric='Contribution per assigned eligible visitor including nonbuyers and other branch purchases',
           stop='Loss/expense above contribution threshold or customer-experience guardrail failure'),
      dict(decision='Peak-hour attachment',chain='POS suggestion → genuinely extra item → preparation/checkout load → possible queue delay → abandoned baskets or service failures → total contribution',
           observed='Pair enrichment, target baskets and historical contribution',unidentified='Incremental attachment, delay, abandonment, added labor',
           protection='Randomize prompt in defined blocks; log all completed and abandoned orders; cap load',
           metric='Total block contribution after labor and waste; wait-time distribution; completion rate',
           stop='Lost-basket or incremental-cost budget exhausted; pre-agreed wait/quality limits breached'),
      dict(decision='Discount policy',chain='Offer assignment → lower contribution on existing demand + possible extra conversion → substitution/time-shift/branch-shift → retention → incremental chain contribution',
           observed='Discount arithmetic and purchased-basket associations; no assigned-visitor data',
           unidentified='Counterfactual purchase, new visits, displacement and retention',
           protection='Assign before purchase; include nonbuyers; compare simultaneous control and offer groups',
           metric='Intention-to-treat contribution per assigned visitor and overall daily chain contribution',
           stop='Net contribution fails pre-registered minimum; cost/quality guardrails breached'),
      dict(decision='Growth and staffing',chain='More baskets per day → workload rises → possible capacity/labor/waste response → retained service quality → net operating contribution',
           observed='Exact growth bridge, evening concentration and stable observed GP per basket',
           unidentified='Capacity, staffing, preparation time, overtime and unmet demand',
           protection='Instrument queues/stockouts before buying demand or adding shifts; use real marginal staffing quotes',
           metric='Contribution per service hour after incremental labor, waste and displaced sales',
           stop='Added contribution does not cover real incremental cost; minimum coverage/quality fails'),
      dict(decision='Customer retention measurement',chain='Loyalty or identifier-capture policy → identification probability changes → observed repeat rate changes → potentially false retention conclusion → misallocated spend',
           observed='About 36.5% of baskets lack customer IDs',unidentified='Missing-customer behavior and customer identity linkage',
           protection='Measure identification rate by arm; stable randomized eligibility; no assumed retention uplift',
           metric='Contribution per assigned cohort with identification/attrition diagnostics',
           stop='Apparent retention benefit disappears under identification sensitivity or cost accounting')]
    pd.DataFrame(chains).to_csv(tables/'causal_chain_register.csv',index=False)
    p=price.set_index('product');water=p.loc['Sparkling Water'];matcha=p.loc['Iced Matcha']
    evening=capacity[capacity.scope.eq('Evening 19–23')].iloc[0]
    stress=upsell_capacity_gates(x,lost_baskets=40)
    stress.to_csv(tables/'upsell_40_lost_baskets_stress.csv',index=False)
    stressed=stress[stress.scope.eq('Evening 19–23')].iloc[0]
    full=counterfactual(x,x,recovery=.5)
    text=f'''# Causal decision chains — protect contribution, customers and service

**The recommendation is conditional:** first validate Garden's cash costs; then test prices or attachment only where whole-basket contribution and service stay healthy. More revenue, higher item margin and larger baskets can each coexist with worse business outcomes.

This document separates **observations**, **accounting identities**, and **hypothesized causal links**. The transaction file identifies arithmetic and associations, not the effects of changing prices, suppliers, staffing or offers. All arrows below are proposed mechanisms until tested. A small p-value for co-purchase does not validate an intervention chain.

## 1. A cost-allocation problem can trigger the wrong operational response

**Hypothesis chain:** branch costing rule → lower recorded Garden GP → management pressure → cheaper supplier or recipe change → possible quality/availability change → possible lost repeat purchases → chain contribution.

**What is observed:** product-branch unit costs never change in the six months; Garden's same-product costs are about 43% above Harbour's. The ${full['matched_gap']:,.2f} recorded difference is real arithmetic. Whether it represents actual avoidable cash costs is unknown.

**Fork in the chain:** if costs are allocations, changing vendors might not remove the expense at all. If invoices confirm a real procurement disadvantage, savings may be available, but lower quality, waste, freight and stockouts can consume them. Neither pathway is established by the CSV.

**Financial gate:** assuming 50% cash recovery, unchanged mix and proportional customer loss, Garden's ${full['net_benefit']:,.2f} hypothetical saving survives at most {full['break_even_demand_loss']:.1%} volume loss before expenses. That is a break-even ceiling, not an acceptable service target. A quality failure can be unacceptable before a financial threshold is reached. If a subjective probability p of real savings is used to value an audit, p × recoverable difference − audit cost is only an assumption-based screening calculation, not measured ROI.

**Protect Stories:** finance reconciles costs to invoices and the cost master first. Procurement compares landed cost per conforming unit, waste and reliability. Operations validates recipes and portions. Reject operational change if savings are allocation-only or specifications fail. Do not penalize a branch manager for an unverified accounting rule.

## 2. Raising a cheap item's margin can put an expensive basket at risk

**Hypothesis chain:** price increase → contribution per retained item rises → customer either drops/substitutes that item OR abandons the purchase → other products' contribution is lost → chain-wide net result.

**New measured exposure:** Garden Sparkling Water contributes ${water.item_gp:,.2f} GP, but all Garden baskets containing it contribute ${water.containing_basket_gp:,.2f}. Its Harbour-price alignment adds only ${water.hypothetical_uplift_before_response:,.2f} at unchanged sales. An item-only calculation tolerates {water.item_only_loss_break_even:.1%} lost item sales; a whole-basket exit pathway tolerates just **{water.whole_basket_loss_break_even:.2%}** of those baskets. The latter is not a prediction; it is a different behavioral assumption.

For Iced Matcha the corresponding thresholds are {matcha.item_only_loss_break_even:.1%} item loss versus **{matcha.whole_basket_loss_break_even:.1%}** complete-basket loss. All 45 products are exported. Product scenarios overlap, so never sum their containing-basket exposure or individual counterfactuals.

**Accounting identity:** U is the price uplift with all current purchases retained; P is current target-item GP; B is GP of all containing baskets. Under representative proportional losses, item-only break-even = U/(P+U), while complete-basket break-even = U/(B+U). Source discounts, costs and remaining product mix are fixed. Real substitution, unequal customer responses or cross-branch recapture change the result.

**Protect Stories:** price-test only with a simultaneous control, stable pre-purchase assignment and visitor/nonbuyer logging. Measure full baskets, alternative products, complaints and other-branch contribution. A Garden win caused solely by moving a Harbour purchase is not a chain win. Customer-ID missingness limits linkage; log assignment and identification coverage explicitly. Reject a change that raises item margin while reducing contribution per eligible visitor after costs.

## 3. A successful upsell can still reduce total evening profit

**Hypothesis chain:** prompt → extra pastry → extra service work → possible longer queue → possible abandoned orders or missed service standards → whole-basket losses offset attachment GP.

**Observed target:** {int(evening.eligible_baskets):,} evening matcha baskets lack bakery. **Assumed response:** a no-discount prompt causes one extra bakery unit in 3% of those baskets. At historical evening bakery contribution, the replay adds **${evening.hypothetical_attachment_gp:,.2f}**, before labor, waste or substitution. Incremental adoption is unknown.

**New loss budget:** historical evening GP/basket is ${evening.observed_gp_per_basket:.2f}. The modeled attachment benefit is erased by **{evening.lost_baskets_break_even:.1f}** representative evening baskets lost across the six-month scope. With 40 lost baskets, the net is **${stressed.net_contribution:,.2f}** before program costs. This does not claim 40 baskets will be lost. It shows how little queue damage this particular assumed uptake can absorb.

**Protect Stories:** compare randomized prompt/no-prompt blocks within comparable branch/daypart exposure; log preparation and checkout times, arrival and completion counts, stockouts, waste and marginal labor. Individual-order randomization can miss harm to other customers sharing the queue. Set block length and washout using measured queue-clearance times; retain all arrivals and completions, not only customers accepting the prompt. Use inference clustered at the assignment block and account for repeated dates. The main outcome is total contribution per assigned service block, not AOV among successful orders. Set acceptable wait/quality thresholds before the test; stop at an operational breach even if average order value rises. Do not convert the loss budget into allowable extra seconds without actual service-time and arrival-rate data.

## 4. Discounts can pay for demand that was already coming

**Hypothesis chain:** offer → lower contribution on existing demand + possible conversion/extra units → product substitution, purchase timing shifts or branch switching → later retention → incremental chain contribution.

**Observed warning:** any-discount baskets mechanically overrepresent larger baskets; fixed-basket shuffled labels reproduce the observed 10% units gap. The 15% GP comparison reverses against Harbour's own baseline. Neither result proves offers are harmful; both show why a selected redeemer comparison is inadequate.

**Protect Stories:** randomize offer eligibility before purchase and include nonbuyers. Analyze contribution per assigned visitor after program and marginal operating costs, plus total chain contribution and repeat behavior over a pre-specified follow-up. Account for product and branch displacement; do not call a moved purchase incremental. Do not add historical discount concessions to claimed cost savings. Existing 0/10/15% campaign estimates and their limitations remain in ../analysis/outputs/REPORT.md.

## 5. Traffic growth can hide a worsening operational business

**Hypothesis chain:** basket volume grows → workload rises → possible extra labor/waste/capacity expense → service and conversion change → operating contribution may diverge from recorded gross profit.

The observed GP/day bridge assigns about 99.2% of January–June growth to more baskets/day; GP/basket changes little. Evening activity is financially important, but no queue, labor or capacity records exist. Therefore the file cannot show that demand exceeded capacity, that staffing is inefficient, or that net profit rose with GP.

**Protect Stories:** obtain actual labor and waste costs and instrument arrivals/completions. Compare adding coverage, moving existing coverage within minimum service constraints, and doing nothing. Use incremental contribution after costs and service quality; do not infer an optimal roster from hourly sales alone.

## 6. A loyalty campaign can improve the metric without improving retention

**Hypothesis chain:** campaign changes willingness to give an ID → a larger share of repeat visits is recognized → observed repeat rate rises → management mistakenly credits retention → budget allocated without incremental contribution.

Around 36.5% of source baskets lack customer IDs. We cannot observe the true repeat rate of anonymous purchasers or estimate a campaign effect from this file. A changing identification mechanism is a plausible bias, not a discovered event.

**Protect Stories:** report identification and attrition by assigned arm, keep assignment independent of later purchases, and include zero-purchase outcomes. Require contribution improvement and sensitivity to unmatched identities before funding expansion. Never call a rise in recognized repeat customers proof of loyalty improvement.

## Decision sequence and stop rules

1. **Verify cash accounting before operational pressure.** No supplier changes justified by an allocation-only difference.
2. **Instrument service before stimulating peak demand.** No staffing or queue effect is inferred from transactions alone.
3. **Test suggestions before rebates.** Any incremental attachment must survive lost-basket, substitution and operating-cost budgets.
4. **Price-test whole baskets, not isolated margins.** Track visitor outcomes and possible chain displacement.
5. **Scale only on incremental contribution and customer/service guardrails.** Pre-register the minimum worthwhile benefit, spending cap, acceptable quality/wait/complaint limits, duration and analysis. These thresholds must come from Stories; they are not fabricated here.

The data support a map of decisions and failure pathways, not a proven causal network. Further evidence could reverse any intervention recommendation. Tables provide reproducible monetary gates and all product exposures; no commercial pilot has been performed.
'''
    (out/'causal_decisions.md').write_text(text)
    return text

if __name__=='__main__':
    run();print('Generated reports/causal_decisions.md and five causal decision tables')
