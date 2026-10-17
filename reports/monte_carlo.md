# Monte Carlo: how sure are the outside-in decisions?

**20,000 draws per decision, seed 490.** Every assumption behind the outside-in chains ([outside_in_chains.md](outside_in_chains.md)) is drawn from a stated distribution and replayed against the transaction file. Hourly GP is bootstrapped over the 181 trading days. Each result is the probability that the action pays plus its six-month value (median, P5–P95). Rebuild: `python scripts/monte_carlo.py`. Draws: `tables/mc_draws.csv.gz`.

## Results

| Decision | P(pays) | Six-month value, median (P5 to P95) |
|---|---|---|
| Close Uptown 07:00–09:00 and Garden 07:00 | 75% | $656 (P5 -$807 to P95 $2,315) |
| Raise every price 5% | 100% | $7,305 (P5 $3,025 to P95 $11,128) |
| Raise 5% but hold coffee | 100% | $6,104 (P5 $3,388 to P95 $8,563) |
| Uniform 5% beats holding coffee | 88% | $1,204 (P5 -$467 to P95 $2,593) |
| Fixed-price matcha contract (value before its premium) | n/a | $1,196 (P5 $513 to P95 $2,602) |
| Harbour: move 11 prices down to $N.95 | 77% | $585 (P5 -$393 to P95 $4,032) |
| Harbour: move them up to $N.25 | 88% | $418 (P5 -$198 to P95 $850) |
| $N.95 beats $N.25 | 61% | $316 (P5 -$968 to P95 $3,537) |

GP overstated by frozen unit costs, March–June: **$6,388 (P5 $2,664 to P95 $10,951)**. The cost drift of non-coffee food explains almost all of the spread.

## What the simulation changed

1. **Opening hours: staffing decides, not the energy shock.** The closure pays in 75% of draws. The inputs that move the answer are recapture (ρ=+0.63), staff (ρ=+0.56), labour realized (ρ=+0.33), wage (ρ=+0.23). The generator tariff barely matters. The chain from Hormuz to the generator tariff is real, but it is a minor driver. Before closing, check whether the early shift really has two people and whether those hours can be removed from the roster.

| Branch-hour | P(saving > 0) | Median | P5 to P95 |
|---|---|---|---|
| Uptown 07:00 | 78% | $247 | -$253 to $795 |
| Uptown 08:00 | 79% | $251 | -$226 to $791 |
| Garden 07:00 | 68% | $164 | -$349 to $737 |

2. **Prices: drop "hold coffee".** A 5% rise pays in 100% of draws because the break-even elasticity at Stories' 58.7% margin is -1.68. That is beyond the whole prior range (−0.25 to −1.5 for categories), so the 100% reflects the prior, not proof. Holding coffee back gives up money in 88% of draws and only wins if coffee demand is far more elastic than the rest of the menu. The revised action is a uniform +5% at one branch for four weeks, measured against the other two. Elasticity is the only input that matters here (ρ≈1.0 in `tables/mc_price_drivers.csv`), so the test is worth more than any further modelling.

3. **Matcha: lock the price.** A six-month fixed-price contract is worth $1,196 (P5 $513 to P95 $2,602) before its premium. Most of that is the price lock, and only a small part is avoided stockouts. Pay a premium below the median and the contract pays in most draws.

4. **Harbour endings: test both directions.** Dropping to $N.95 beats rounding up to $N.25 in only 61% of draws. The answer turns on item elasticity:

| Item elasticity | P($N.95 beats $N.25) |
|---|---|
| below −2 | 100% |
| −2 to −1.5 | 99% |
| −1.5 to −1.25 | 75% |
| −1.25 to −1 | 54% |
| −1 to −0.75 | 31% |
| −0.75 to −0.5 | 10% |
| above −0.5 | 0% |

Run the Harbour A/B with three arms (today, $N.95, $N.25), not two.

## Inputs

| Module | Input | Distribution | Basis |
|---|---|---|---|
| Opening hours | Staff on the early shift | 1 (40%) or 2 (60%) | Assumption |
| Opening hours | Loaded wage per staff-hour | Triangular $1.80 / $2.60 / $3.50 | Minimum wage 28M LBP ≈ $312/mo; barista ≈ $450 + charges |
| Opening hours | Share of closed staff-hours actually removed | Uniform 50–100% | Assumption (bake-off and receiving may keep someone in) |
| Opening hours | Electricity per open hour | Triangular 1.5 / 3 / 5 kWh | Espresso standby 0.33 kWh/h + brewing, lights, HVAC |
| Opening hours | Generator share of marginal kWh | Uniform 60–100% | EDL supplied 4–9 h/day in 2026 |
| Opening hours | Generator tariff, next 6 months | Uniform $0.45–$0.59/kWh | Ministry tariffs Mar–Sep 2026 |
| Opening hours | Customers who come back later | Beta(2,3), mean 40% | Assumption |
| Opening hours | Demand level | Uniform between H1 average and June run-rate | Chain 1: growth may not be real |
| Opening hours | Sampling noise in hourly GP | Bootstrap of the 181 trading days | Data |
| Costs and prices | Coffee cost drift since cost master | Triangular −4% / +1% / +7% | Arabica −16% × bean share, plus dairy and packaging |
| Costs and prices | Other food cost drift | Triangular 0% / +7% / +18% | Food CPI +15% → +18% y/y |
| Costs and prices | Matcha powder per drink | Uniform 2–4 g | Assumption |
| Costs and prices | Matcha landed price rise | Triangular +$15 / +$60 / +$120 per kg | Tencha auctions +22% to +80% y/y |
| Costs and prices | Category price elasticity | Triangular −1.5 / −0.8 / −0.25 | Food away from home −0.7 to −0.8; coffee −0.26 |
| Costs and prices | Coffee elasticity multiplier | Uniform 1.0–1.5× | Coffee is the most price-compared item (assumption) |
| Matcha supply | Chance of a supply disruption in 6 months | Uniform 5–30% | Japanese suppliers rationing since 2025 |
| Matcha supply | Disruption length | Uniform 7–28 days | Assumption |
| Matcha supply | Matcha buyers who switch drink | Uniform 30–80% | Assumption |
| Price endings | Left-digit bias θ | Beta(0.66, 2.09): mean 0.24, IQR 0.06–0.37 | Strulov-Shlain (2023) product estimates |
| Price endings | Item elasticity multiplier | Uniform 1.0–2.0× category elasticity | Items substitute within the menu |

## Limits

Constant-elasticity demand ignores customers who leave for a competitor for good, and that is the real risk of any price rise. No cross-item substitution is modelled except through the item-elasticity multiplier. Draws are independent except where one module feeds another (matcha cost → contract value; category elasticity → item elasticity). The simulation measures how far our assumptions spread the answer. It does not validate the assumptions; the field tests do that.
