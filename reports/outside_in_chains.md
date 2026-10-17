# Outside-in: what the till cannot tell you about Lebanon's first half of 2026

**Bottom line for the CEO.** Five chains of cause connect this transaction file to sourced facts about Lebanon between January and June 2026. Each one changes a decision. (1) The file does not register the 2 March war. Lebanon's restaurant syndicate reports a fall of more than 85% after that date. The file shows a statistical step of **+4.0%** (95% CI -2.7% to +11.2%). Do not plan capacity, leases or forecasts on this growth until the till is reconciled with cash and card settlements. (2) The Strait of Hormuz shock raised the generator tariff by **74%** between January and April. With two people on shift [A], 3 early-morning branch-hours earn less GP than they cost in staff and electricity, even if every one of their customers is lost. The worst is Uptown's 07:00 hour, which averages $4.37 GP against $6.53 of cost. The Monte Carlo puts the chance that closing pays at 75%; staffing decides it more than energy does. (3) Menu prices and unit costs did not change for 181 days. Restaurant prices nationally were rising ~16% year on year. Each 5% of unrecorded cost inflation since March overstates GP by **$4,608**. (4) The existing team's flagship pilot pushes matcha. Japan has rationed matcha since 2025, and 2026 tencha auctions set records. Run the same no-discount attachment pilot on coffee, where arabica fell ~16%. (5) The Harbour price list is Garden × 1.05 applied to every item. 11 items cross a whole-dollar line by a few cents, which is the most expensive place for a price to sit.

Every link below is labelled **[D]** (measured in the CSV), **[R]** (external fact, sourced in [`data/external/outside_research_2026.csv`](../data/external/outside_research_2026.csv)), **[I]** (our inference) or **[A]** (assumption you can change). Rebuild with `python scripts/outside_in_chains.py`. Tables are in `reports/tables/outside_*.csv`.

---

## Chain 1 — The war the till never heard

| # | Link | Type |
|---|---|---|
| 1 | 28 Feb: US–Israeli strikes on Iran; Hormuz effectively closed. 2 Mar: Hezbollah–Israel war resumes. Beirut is struck on 3–4 Mar, its southern suburbs are ordered evacuated on 5 Mar, the Ramlet al-Baida seafront is hit on 12 Mar, central Beirut on 18–19 Mar, and ≥92 people are killed in Beirut on 8 Apr. 1.2 million people are displaced. | R |
| 2 | Stories Coffee is a Beirut chain (22 branches in 2025: Ain El Mreisseh, Ramlet El Bayda, Bir Hassan, Verdun, Bliss, Khalde, Saida…). Bir Hassan borders the evacuated southern suburbs, and Ramlet El Bayda is the seafront struck on 12 March. The file's three branch names are anonymised. | R |
| 3 | Restaurant syndicate (Tony Ramy): +25% in Jan–Feb, then **a fall of more than 85% over the next four months**. Economic Organizations (Choucair): "the nightlife sector completely died". 60% of Beirut/Mount Lebanon service firms report lower H1 revenue (average −54%). 60% of firms raised prices and 38% cut hours. | R |
| 4 | Baskets/day: 164.1 before the war → **186.3** during it (Mar 2–Apr 15). GP/day: $869 → $985. | D |
| 5 | A model with a step at 2 March (branch × weekday effects, branch trends, week-clustered SEs) estimates **+4.0%** (95% CI -2.7% to +11.2%). Shifting the break to every date from 1 Feb to 31 May gives steps of -4.8% to +5.8%. 12% of those arbitrary dates give a step at least as large as 2 March. The war date does not stand out from ordinary noise. **Power check:** randomly deleting just 10% of post-war baskets yields an estimated step of -7.3% (CI -13.3% to -0.9%), and planting the syndicate's 85% fall yields -86.8%. The model would have seen even a small fraction of the sector's decline. | D |
| 6 | Beirut's worst days look ordinary against the trend model (observed ÷ expected; table below). The day Israel first struck Beirut (3 Mar) ran **+18% above trend**, busier than 98% of all days in the half-year. | D |
| 7 | Behaviour that a war should move does not move. Evening share is 44.5% → 44.5%; 22:00–24:00 share 13.8% → 14.7%; dine-in 59.0% → 59.6%; GP/basket $5.29 → $5.29. | D |
| 8 | A displacement inflow, like the one that filled Hamra's cafés in 2024, would show a step **up** and a burst of new faces. The file has no step. New identified customers by month: Jan 1,979 · Feb 843 · Mar 433 · Apr 159 · May 60 · Jun 20, the decay of a fixed customer pool. Only 647 of 3,494 IDs first appear after 2 March. | D/R |
| 9 | The file shows the marks of a formula. All 45 Harbour prices equal Garden × 1.05 (100% exact) and Uptown equals Garden × 0.96 (100%). Garden's costs equal Harbour × 1.43 (100%). Prices and costs never change (max 1 value per product-branch). Every one of 25 Tuesdays runs 1.36–1.55× its neighbours, with no discount, mix or basket change. | D |
| 10 | **Inference:** either this extract is not a faithful record of trading at Lebanese branches in H1 2026 (re-dated, re-scaled or simulated), or Stories experienced an unusual H1 that needs to be explained before anyone extrapolates it. Either way, the +57% Jan→Jun growth in baskets/day cannot be used for decisions as it stands. | I |

| Date | Beirut event | Baskets | Model-expected | Ratio |
|---|---|---|---|---|
| 03 Mar (Tue) | IDF strikes on Beirut | 303 | 257 | 1.18 |
| 05 Mar (Thu) | Southern-suburb evacuation order | 189 | 166 | 1.14 |
| 12 Mar (Thu) | Ramlet al-Baida seafront strike (02:00) | 166 | 169 | 0.98 |
| 18 Mar (Wed) | Central Beirut strikes | 162 | 176 | 0.92 |
| 19 Mar (Thu) | Central Beirut strikes | 175 | 172 | 1.02 |
| 08 Apr (Wed) | >=92 killed in Beirut | 187 | 187 | 1.00 |
| 09 Apr (Thu) | Southern-suburb evacuation order | 183 | 182 | 1.00 |

**Decision.** Freeze any capacity, lease, hiring or forecast decision that relies on the H1 growth trend, and reconcile the till first. That includes the existing finding that 99.2% of GP growth came from more baskets per day. The test is cheap and physical: compare daily POS totals with card-acquirer settlements and cash deposits for 25 Feb–15 Apr, and compare cup and lid purchases with takeaway drink units. If the POS is right, chain-wide takeaway cup use rose from **47/day in January to 77/day in June** (+63%). Supplier invoices either show that or they don't. **What would prove us wrong:** settlements that match the POS day for day through March. In that case Stories outperformed its sector by roughly 90 points, and the next question is why (relative price, displaced customers, or competitors closing), because none of those is permanent.

---

## Chain 2 — Hormuz → diesel → generator tariff → the hours that cost more than they earn

| # | Link | Type |
|---|---|---|
| 1 | Hormuz has been effectively closed since 28 Feb. Brent averaged ~$103 in March, up ~65% in a month, the largest monthly rise on record. It touched $126 on 28 Apr. | R |
| 2 | Lebanon's diesel benchmark (20 L): 1.40M LBP in February → 2.48M LBP in April (+77%). | R |
| 3 | The state grid (EDL) fell from 7–9 h/day in February to ~4 h/day by July. Private diesel generators fill the gap, and fuel is ~82% of their cost. | R |
| 4 | The Ministry of Energy generator tariff, converted at 89,500 LBP/USD: Jan $0.317 → Feb $0.338 → Mar $0.453 → Apr $0.552 → May $0.517 → Jun $0.469 per kWh. September 2026 reached ~$0.59. | R |
| 5 | Keeping a branch open one more hour costs staff plus electricity. Base case [A]: 2 staff × $2.60/h (minimum wage 28M LBP ≈ $312/month, barista ≈ $450 + charges) and 3 kWh (a 2-group espresso machine alone draws 0.33 kWh/h on standby). That is **$6.15/h in January → $6.86/h in April**. | R/A |
| 6 | GP earned in the opening hour, per day: Uptown 07:00 **$4.37** (0.81 baskets), Garden 07:00 $5.49 (1.31), Harbour 07:00 $11.35 (1.88). For comparison, Uptown 23:00 earns $10.08. | D |
| 7 | Garden sells at a 46.9% recorded margin because of its × 1.43 costs, so each of its baskets earns the chain's lowest GP. In a thin hour the costing rule and the energy shock compound. | D |
| 8 | Branch-hours whose six-month GP is below their base-case cost are listed below. Closing them pays **even if every one of those customers is lost**. | D/A |
| 9 | Some early customers would come back later in the morning [A]. With 50% recapture the saving roughly doubles. For these branch-hours the break-even recapture is below zero, so closing pays even with no recapture. | A |
| 10 | 38% of Lebanese firms already cut hours in H1 2026 (InfoPro). Stories' file shows the same 07:00–24:00 schedule every day. | R/D |

| Branch-hour | Baskets/h | GP/h | Base cost/h | 6-mo saving, 0% recapture | 6-mo saving, 50% recapture | 6-mo saving, low-cost case (1 staff, 1.5 kWh), 0% recapture |
|---|---|---|---|---|---|---|
| Uptown 07:00 | 0.81 | $4.37 | $6.53 | $391 | $786 | -$344 |
| Uptown 08:00 | 1.01 | $4.96 | $6.53 | $283 | $732 | -$452 |
| Garden 07:00 | 1.31 | $5.49 | $6.53 | $188 | $685 | -$547 |

Under the low-cost case (one person on shift), none of these hours is negative, and closing needs 44%–55% of their customers to return later. Volume also matters: Uptown 07:00 earned $3.53/h in January and $6.41/h in June. If the growth trend is real (chain 1), these hours are getting close to break-even. If it is not, they are not.

**Decision.** Open Uptown at 09:00 and Garden at 08:00 for a four-week test, and stop treating opening hours as fixed. The base-case saving is $862 per six months with no recapture and $2,203 with 50%, across three branches. Stories has 22 branches, so the rule matters more than these three numbers. The Ministry publishes the generator tariff every month. Add a standing rule: *close a branch-hour when its trailing 8-week GP per hour falls below staff cost plus kWh × that month's tariff.* Uptown 23:00 ($10.08/h) is the next hour to watch if the tariff keeps rising (September: ~$0.59/kWh). **What would make this wrong:** if the early hour has to be staffed anyway for bake-off and delivery receiving, labour savings shrink. In that case only the electricity and front-of-house hours are saved, and the low-cost column is the right one to read. The Monte Carlo puts the chance this pays at 75%. The tariff barely moves that answer. Staffing (one or two people on the early shift) and the share of customers who return later decide it, so confirm the roster first. Measure with a 4-week switch and compare baskets in each branch's first two open hours with the same hours at Harbour, which stays at 07:00 (difference-in-differences).

---

## Chain 3 — A frozen menu in a 20% inflation year

| # | Link | Type |
|---|---|---|
| 1 | Oil and shipping shock plus war: headline CPI went from 10.9% (Jan) to 17.3% (Mar) and **20.0% (Apr)** year on year, +3.0% in April alone. | R |
| 2 | Food & non-alcoholic beverages: 15.1% → 18.0% y/y. Water/electricity/fuels: 3.7% → **41.4%**. | R |
| 3 | Restaurants & hotels prices: 7.2% → **16.0%** y/y. 60% of firms raised prices. | R |
| 4 | Stories' file has **zero** price changes and **zero** unit-cost changes across 135 product-branch cells and 181 days. | D |
| 5 | So recorded unit cost is a standard cost, not the landed cost. Recorded GP (58.7% margin) is the margin Stories would earn at the prices on the day the cost master was last updated. | I |
| 6 | Mar–Jun COGS on the file is $92,150. Each 5% of unrecorded cost inflation overstates Mar–Jun GP by **$4,608** (3.5%). At the national food-inflation rate (18%) it is **$16,559**. | D/A |
| 7 | Inputs did not move together. Arabica fell ~16% (Jan 16 → Jun 16, record Brazil crop). Cocoa fell ~37% to April, then rebounded. Matcha leaf hit records (chain 4). Diesel rose 77%. Costs moved in different directions, so the cost master needs refreshing item by item. | R |
| 8 | Stories held prices while the market rose ~16%, so its relative price fell. That alone could pull customers in, and it is one possible "real" explanation for chain 1 if settlements confirm it. | I |
| 9 | A 5% increase breaks even at a 7.9% volume loss at the chain margin. The national restaurant index accelerated by ~9 points y/y between January and April, so a 5% rise would probably still leave Stories relatively cheaper than in January. | D/I |
| 10 | A lower true margin makes a price rise more attractive, because each lost unit was earning less than the books say. The cost refresh and the price test belong together. | I |

**Decision.** (a) Refresh the cost master monthly from invoices, starting with the 10 highest-volume items. This turns "GP" back into a number that can be acted on. (b) Test a uniform +5% at one branch for four weeks against the other two. The Monte Carlo ([monte_carlo.md](monte_carlo.md)) shows that holding coffee back while raising the rest loses to a uniform rise in most draws, even though arabica fell. Hold coffee only if the test shows its demand is far more elastic than the rest of the menu. **What would make this wrong:** if Stories hedged or pre-bought six months of inputs in December, the frozen costs could be close to correct until the stock ran out. Ask procurement for the stock-cover dates.

---

## Chain 4 — The evening runs on a rationed powder

| # | Link | Type |
|---|---|---|
| 1 | Japan's 2024–25 heat cut tencha (matcha leaf) yields while global demand boomed. In 2025 Ippodo and Marukyu Koyamaen limited purchases and raised all prices. | R |
| 2 | 2026 tencha auctions set records: Kagoshima averaged ¥19,095/kg on 14 May (**+80% y/y**) and Uji opened ~22% higher. | R |
| 3 | The Hormuz-driven freight and insurance rise adds to the landed cost in Beirut (the CPI transport component rose 33% y/y in April). | R/I |
| 4 | Matcha drinks are 8.1% of morning units, **13.1% of evening units**, and the evening is the chain's largest GP block. | D |
| 5 | Matcha drinks: 5,771 units and $23,354 GP over 6 months ($129/day). The recorded cost never moves. | D |
| 6 | At 3 g of powder per drink and +$60/kg landed [A], each drink costs **$0.18** more. That is $1,039 per six months (4.4% of matcha GP), and the range across the assumptions is $346–$2,308. | A |
| 7 | The bigger exposure is availability. A 14-day matcha stockout costs $1,806 GP if customers walk away and $903 if half switch to another drink. | D/A |
| 8 | The existing team's flagship recommendation is a matcha + bakery attachment pilot. Its eligible baskets exist only while matcha is in stock, so a shortage switches the pilot off in the evening, when matcha is most important. | D/I |
| 9 | Coffee is the opposite case: arabica is down ~16%, and the recorded margin is 66.1% on Cold Coffee and 66.6% on Hot Coffee, against 60.9% on Matcha & Tea. The repository's own basket-size null model already shows Bakery + Cold Coffee enriched 1.18× (Jan–Apr, q=0.018) and 1.23× (May–Jun, q=0.018); Bakery + Matcha is the stronger pairing at 1.76× / 1.72×. | R/D |
| 10 | Pointing the same pilot design at Cold Coffee + Bakery gives up some pairing strength. In exchange it targets a pairing that replicates in both periods, carries a higher recorded margin, and runs on an input whose cost is falling. | I |

**Decision.** (a) Point the no-discount attachment pilot at Cold Coffee + Bakery in the evening, and keep Matcha + Bakery as a second arm only if supply is contracted. (b) Lock a 6–12-month matcha contract or dual-source culinary grade (Kagoshima, Shizuoka or Korean) for Iced and Strawberry Matcha, which are mixed with milk and fruit. (c) Re-cost the three matcha SKUs at the next invoice, and price Strawberry Matcha (lowest matcha margin) first. **What would make this wrong:** a fixed-price matcha contract signed before the 2026 auctions would make the cost risk temporary. Check its expiry.

---

## Chain 5 — Formula prices land on the wrong side of the dollar

| # | Link | Type |
|---|---|---|
| 1 | Lebanon runs on dollar cash: the cash economy was 45.7% of GDP (World Bank, 2023). Customers read and pay these menus in dollars. | R |
| 2 | Garden prices are hand-set: **100%** end in 0 or 5 cents (4.85, 9.65, 5.75…). | D |
| 3 | Harbour is Garden × 1.05 for every item, so only 11% of its prices end in 0/5 (5.09, 10.13, 6.04…). Uptown, at × 0.96, has 18%. | D |
| 4 | Left-digit bias: shoppers treat a 1-cent move off a .99 ending as if it were >20 cents, and retailers forgo **1–4% of gross profit** by under-using price endings (Strulov-Shlain, *Review of Economic Studies*, 2023). | R |
| 5 | The 5% formula pushes 11 Harbour items just across a whole dollar (≤20¢ over). Garden's charm price becomes Harbour's worst price point. | D |
| 6 | Those items sold 6,570 units at Harbour in six months. | D |
| 7 | Setting them to $N.95 gives up $918 at constant volume. Each item breaks even with a 1.6%–7.7% unit gain. The paper finds that shoppers perceive a move across the dollar as many times its cents, so gains of this size are plausible. They are not proven, and the test settles it. | D/R |
| 8 | Odd-cent prices also make change-making harder at the 21:00 peak (the busiest hour) in a cash-dollar market where cents are settled in lira [A, verify at the till]. | A |
| 9 | Harbour, the highest-margin branch (65.0%), carries the price-point penalty. Garden's hand-set endings do not. | D |
| 10 | Replace "× 1.05" with a branch price ladder: Garden price + a fixed premium, snapped to .25/.50/.75/.95. | I |

| Item | Garden | Harbour now | Proposed | Harbour units | Revenue given up (const. volume) | Break-even unit gain |
|---|---|---|---|---|---|---|
| Iced Matcha | $6.85 | $7.19 | $6.95 | 1,121 | $269 | 5.4% |
| Iced Americano | $3.85 | $4.04 | $3.95 | 767 | $69 | 2.9% |
| Strawberry Matcha | $7.65 | $8.03 | $7.95 | 725 | $58 | 1.7% |
| Almond Croissant | $4.85 | $5.09 | $4.95 | 618 | $87 | 4.6% |
| Still Water | $1.95 | $2.05 | $1.95 | 577 | $58 | 7.7% |
| Cheesecake Slice | $6.75 | $7.09 | $6.95 | 561 | $79 | 3.6% |
| Caramel Latte | $5.75 | $6.04 | $5.95 | 515 | $46 | 2.2% |
| Fresh Orange Juice | $5.75 | $6.04 | $5.95 | 486 | $44 | 2.3% |

**Decision.** Re-tier the Harbour menu once, as a reprint with no change to costs. The Monte Carlo shows that dropping to $N.95 beats rounding up to $N.25 only when item demand is elastic (beyond about −1.25), so test three arms (today, $N.95, $N.25) in alternating weeks at Harbour for 8 weeks, with Garden and Uptown as controls. Measure units and GP per item for the re-tiered items only, plus total basket GP. **What would make this wrong:** if Harbour customers are price-insensitive, the left-digit response may be weak, and then rounding *up* to $N.25 is the better ladder. The test tells you which.

---

## How this changes the existing recommendations

| Existing recommendation | Outside-in adjustment |
|---|---|
| Growth: "99.2% of GP growth is more baskets/day" | Reconcile the till against settlements and cup purchases before using the trend (chain 1). |
| Garden costing audit | Still valid. Garden's bottled water carries the same × 1.43 as its hand-made drinks, so waste and recipes cannot explain it, which points to a costing rule. Add a monthly cost-master refresh (chain 3). |
| Evening service protection | Price each evening hour at the current generator tariff. Trim the opening hours that fail the rule (chain 2). |
| Matcha + bakery attachment pilot | Run it on Cold Coffee + Bakery first. Secure matcha supply before stimulating demand for it (chain 4). |
| Harbour price alignment | Re-tier price endings before any across-the-board increase (chain 5). |

## Limits

External figures come from news, industry and vendor sources and are approximate. The generator tariff applies to subscriber meters, and a branch on EDL or with its own generator pays a different marginal rate. Branch locations are anonymised, so we cannot map Harbour, Garden and Uptown to real streets. Staffing, energy and matcha-dose figures are assumptions, shown with low/base/high values. The file itself may be simulated or re-dated (chain 1). The other four actions (hour rule, cost refresh, matcha sourcing, price ladder) do not depend on its demand figures being real, because they rest on the menu, the costs and Lebanon's 2026 prices. Every action is set up as a measurable test with a stated failure condition. None is a forecast.
