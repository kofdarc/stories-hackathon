# Feature loop: what 81 new features taught us

**Stories' demand is set by the clock, not the sky.** A template of branch × hour × weekday plus a growth trend predicts unseen May–June branch-hours with MAE 1.590 baskets. Pure Poisson chance around that template would give 1.570. The template is therefore within **1.2% of the best any forecast can do**. Holdout dispersion is 1.05, where 1.00 means the remaining variation is pure arrival randomness. Adding every hourly weather, dust and calendar feature changes MAE to 1.594. Weather and calendar without the clock reach R² 0.24, against 0.62 for the template. **Decision:** stop searching for external demand drivers and staff from the clock template. Size buffers with Poisson quantiles (`tables/staffing_template.csv`). Treat exact Poisson behaviour as one more sign that this file is simulated: real café traffic is usually overdispersed by weather, events and local shocks. Reconcile with real POS data before committing capital.

## The loop
Each round tested a hypothesis, kept what replicated in both Jan–Mar and Apr–Jun after a false-discovery correction, and fed the next round.

| Round | Hypothesis / feature | Result | Kept? |
|---|---|---|---|
| 0 | Weather, holidays, Ramadan, payday, dust, bridge days, school breaks (81 columns) | Daily effects all near zero after branch × weekday + trend controls. More features made the daily forecast worse. See [external_factors.md](external_factors.md) | Null |
| 1 | Screen every feature × 8 basket outcomes, within branch × month, BH-corrected, split-half replication | Strongest hits are sunset, daylight, UV and hourly temperature on dine-in and cold share. All of these are proxies for the clock hour | Redirect |
| 2 | Rescreen within branch × month × **hour** | Every weather effect disappears. What remains is the discount mechanics already documented in `analysis/` | Null |
| 3 | Does the evening switch follow sunset or the clock? | Clock. Dine-in jumps at 18:00 in every month (sunset moves from 17:40 to 19:55) and every branch | **Kept** |
| 4 | Temperature → discounts? | Spurious. Two 8-day 15% campaigns (12–19 Mar and 12–19 May), already analysed in `analysis/outputs/REPORT.md` | Dropped |
| 5 | Is dine-in worth more? | No. Within each regime dine-in and takeaway baskets have the same GP, units and mix | **Kept** (seats, not margin) |
| 6 | Clock template vs weather at branch-hour level, May–June holdout | Template R² 0.62; weather adds -0.001 | **Kept** |
| 7 | Is anything left to find? Poisson dispersion test | Dispersion 0.98 train, 1.05 holdout; MAE 1.2% above the noise floor | **Conclusion** |

## Three clock regimes
- **07–10:** cold-drink share of hot + cold drinks 46%, dine-in 46%. Bakery and hot coffee lead.
- **11–17:** cold share steps to 57% at 11:00, dine-in stays at 46%.
- **18–23:** dine-in jumps to 72% at 18:00 and cold share to 70% at 19:00. Cold coffee, matcha and desserts rise. GP per basket is $5.32 dine-in vs $5.38 takeaway (daytime $5.33 vs $5.27).

The steps are identical in every month even though the mean temperature rises by about 11°C, so iced-drink demand here is an **evening occasion, not a heat response**. Plan ice, cold-brew prep, dessert stock and seating by hour of day. A seasonal "summer iced" push has no support in this file. Because dine-in earns the same as takeaway, the evening's binding resource is seats and prep, not menu margin. The busiest planning cell is Harbour on Tuesday at 21:00: 21.3 expected baskets in June, P90 27.

## Limits
Clock hours are bins from transaction time stamps; opening hours, seats, staff and queues are not in the file. The Poisson floor assumes the template's rates are correct; the 1.2% gap is the room left for every unobserved factor combined. Steps that are this sharp and this uniform across branches and months look like generator rules, like the Tuesday spike and the ×1.05 price list documented in [outside_in_chains.md](outside_in_chains.md).
