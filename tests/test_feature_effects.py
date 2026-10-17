"""Effect engine: planted effects are found, confounders are exposed, notebook code compiles."""
import ast
import unittest
import numpy as np
import pandas as pd
from src.feature_effects import CATALOG, OUTCOMES, effect, controls, feature_curve

def synthetic(seed=0, days=180):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({'date': np.repeat(pd.date_range('2026-01-01', periods=days), 40)})
    d['month'] = d.date.dt.strftime('%Y-%m'); d['branch'] = rng.choice(['A', 'B'], len(d))
    d['hour'] = rng.integers(7, 24, len(d)); d['campaign_window'] = False
    return d, rng

class EffectEngineTests(unittest.TestCase):
    def test_planted_flag_effect_is_recovered(self):
        d, rng = synthetic()
        d['rainy'] = rng.random(len(d)) < .3
        d['dine_in'] = (rng.random(len(d)) < .5 + .1*d.rainy).astype(float)
        r = effect(d, 'rainy', d.rainy.astype(float), 'dine_in', controls('rainy', 'dine_in'))
        self.assertLess(r['ci_low'], 10); self.assertGreater(r['ci_high'], 10); self.assertGreater(r['t'], 5)

    def test_seasonal_confounder_vanishes_under_controls(self):
        d, rng = synthetic(1)
        winter = d.month.isin(['2026-01', '2026-02'])
        d['rainy'] = rng.random(len(d)) < np.where(winter, .6, .1)   # rain clusters in winter
        d['dine_in'] = (rng.random(len(d)) < np.where(winter, .3, .6)).astype(float)  # season, not rain
        raw = effect(d, 'rainy', d.rainy.astype(float), 'dine_in', None)
        ctl = effect(d, 'rainy', d.rainy.astype(float), 'dine_in', controls('rainy', 'dine_in'))
        self.assertLess(raw['t'], -5); self.assertLess(abs(ctl['t']), 3)

    def test_controls_never_absorb_the_feature(self):
        for f in CATALOG:
            for o in OUTCOMES:
                s = controls(f, o)
                self.assertNotIn(f, s)
                if f in ('hour', 'daypart'): self.assertNotIn('hour', s)
                if f in ('weekday', 'weekend'): self.assertNotIn('weekday', s)

    def test_curve_controlled_mean_preserves_overall_mean(self):
        d, rng = synthetic(2); d['temp_mean'] = rng.normal(18, 4, len(d)); d['gp'] = rng.normal(5, 1, len(d))
        c = feature_curve(d, 'temp_mean', 'gp', controls('temp_mean', 'gp'))
        self.assertAlmostEqual((c.controlled*c.n).sum()/c.n.sum(), d.gp.mean(), places=8)

    def test_notebook_cells_are_valid_python(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
        import build_notebook
        for cell in build_notebook.CELLS:
            if cell.cell_type == 'code': ast.parse(cell.source)

if __name__ == '__main__': unittest.main()
