"""Financial gates for plausible causal pathways; no causal effects are estimated."""
import numpy as np
import pandas as pd
from .analytics import baskets,matched_products,counterfactual
from .deep_insights import attachment_cases


def price_retention_gates(x, reference):
    """Compare losing an item with losing its containing basket after alignment.

    Both thresholds assume proportionate representative losses and unchanged
    remaining mix, costs and discounts. Individual product scenarios overlap;
    adding them would double-count basket losses.
    """
    g=x[x.branch.eq('Garden')];o=baskets(g)
    refs=reference[reference.branch.eq('Harbour')].groupby('product').price.mean()
    rows=[]
    for product,d in g.groupby('product'):
        if product not in refs:continue
        # Source prices are constant for this snapshot. Realized discounted
        # revenue scales proportionally with the proposed list price alignment.
        multiplier=refs[product]/d.price
        uplift=float((d.revenue*(multiplier-1)).sum())
        affected=o.loc[o.index.isin(d.transaction)]
        item_gp=float(d.gp.sum());basket_gp=float(affected.gp.sum())
        rows.append(dict(product=product,affected_baskets=len(affected),
            list_price_current=float(d.price.mean()),list_price_reference=float(refs[product]),
            hypothetical_uplift_before_response=uplift,item_gp=item_gp,containing_basket_gp=basket_gp,
            item_only_loss_break_even=uplift/(item_gp+uplift) if item_gp+uplift>0 else np.nan,
            whole_basket_loss_break_even=uplift/(basket_gp+uplift) if basket_gp+uplift>0 else np.nan,
            share_of_basket_gp_from_other_items=(basket_gp-item_gp)/basket_gp if basket_gp else np.nan))
    return pd.DataFrame(rows).sort_values('whole_basket_loss_break_even') if rows else pd.DataFrame()


def upsell_capacity_gates(x, adoption=.03, expense=0., lost_baskets=0., displaced_gp=0.):
    """One added bakery unit to matcha-only baskets; subtract complete lost baskets.

    Displaced GP is a separately assumed total from product substitution. The
    user must avoid counting the same lost basket/product twice. These are
    stress scenarios, not measured abandonment, incremental adoption or delay.
    """
    if not 0<=adoption<=1 or min(expense,lost_baskets,displaced_gp)<0:
        raise ValueError('Use adoption in [0,1] and nonnegative costs/losses')
    rows=[]
    for scope,d in [('All hours',x),('Evening 19–23',x[x.hour.between(19,23)])]:
        if d.empty or not {'Matcha & Tea','Bakery'}.issubset(set(d.category)):continue
        case=attachment_cases(d).iloc[0]
        o=baskets(d);added_units=case.eligible_a_only_baskets*adoption
        contribution=added_units*case.attached_unit_gp
        lost_gp=float(o.gp.mean())
        rows.append(dict(scope=scope,eligible_baskets=int(case.eligible_a_only_baskets),
            existing_pair_baskets=int(case.existing_pairs),assumed_adoption=adoption,
            assumed_added_units=added_units,attached_unit_gp=float(case.attached_unit_gp),
            hypothetical_attachment_gp=contribution,observed_gp_per_basket=lost_gp,
            assumed_expense=expense,assumed_lost_baskets=lost_baskets,
            assumed_displaced_gp=displaced_gp,
            net_contribution=contribution-expense-lost_baskets*lost_gp-displaced_gp,
            lost_baskets_break_even=(contribution-expense-displaced_gp)/lost_gp if lost_gp>0 else np.nan,
            maximum_extra_cost_per_attachment=float(case.attached_unit_gp)))
    return pd.DataFrame(rows)


def procurement_quality_gates(x,reference):
    """Recorded savings versus proportional Garden basket loss, at fixed mix."""
    rows=[]
    for recovery in [.25,.5,.75,1.]:
        r=counterfactual(x,reference,recovery=recovery)
        rows.append(dict(assumed_cash_recoverable_fraction=recovery,
            hypothetical_saving_before_losses=r['net_benefit'],
            proportional_garden_basket_loss_break_even=r['break_even_demand_loss']))
    return pd.DataFrame(rows)
