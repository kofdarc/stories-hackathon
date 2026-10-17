"""Build notebooks/feature_effects.ipynb: every feature and its effect, runnable locally or in Colab.

Run: python scripts/build_notebook.py [--execute]
"""
import argparse
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'notebooks' / 'feature_effects.ipynb'

def md(text): return nbf.v4.new_markdown_cell(text.strip())
def code(text): return nbf.v4.new_code_cell(text.strip())

CELLS = [
md('''
# Stories Coffee: every feature and its effect

This notebook adds 81 features to the Stories transaction file and tests each one against nine outcomes, both **raw** and **controlled**. The features cover the clock, weather, air quality, calendar, basket composition and customer history. Each result gets a plain verdict.

**Bottom line (re-derived below):** only the clock matters. Hour, daypart and weekday move demand, dine-in and drink mix strongly. Weather, dust, holidays, Ramadan and customer history do not. Many of them *look* like they matter until branch, season and hour are held fixed. A clock template predicts hourly demand within about 1% of the best any forecast can do.

**Run it**
- **Locally:** open from the repository with the project virtual environment; the notebook finds `stories_transactions.csv` at the repository root.
- **Colab:** run the first cell and upload two files when prompted. One is `stories-coffee-source.zip`, which you build with `python scripts/package_submission.py`. The other is the authorized `stories_transactions.csv`. The raw CSV is never bundled with the code.
'''),
code('''
import os, sys, subprocess, zipfile
from pathlib import Path
IN_COLAB = 'google.colab' in sys.modules
if IN_COLAB:
    from google.colab import files
    print('Upload stories-coffee-source.zip and stories_transactions.csv')
    uploaded = files.upload()
    with zipfile.ZipFile('stories-coffee-source.zip') as z: z.extractall('stories')
    if Path('stories_transactions.csv').exists(): Path('stories_transactions.csv').replace('stories/stories_transactions.csv')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'plotly', 'scipy'], check=True)
    ROOT = Path('stories').resolve()
else:
    ROOT = Path.cwd() if (Path.cwd() / 'src').exists() else Path.cwd().parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
assert (ROOT / 'stories_transactions.csv').exists(), 'Place stories_transactions.csv at the repository root'
print('Working in', ROOT)
'''),
code('''
import numpy as np, pandas as pd
import plotly.express as px, plotly.io as pio
pio.renderers.default = 'colab' if IN_COLAB else 'notebook_connected'
pd.set_option('display.max_rows', 200); pd.set_option('display.width', 200)
px.defaults.template = 'plotly_white'
VERDICTS = ['Replicated effect', 'Unreplicated (one half only)', 'Confounded (raw only)', 'No effect',
            'Mechanical or selection', 'Absorbed by controls']
COLORS = dict(zip(VERDICTS, ['#547965', '#b38b61', '#ae664d', '#d8cfc2', '#9a9a9a', '#e9e4dc']))
from src.analytics import load_data
from src.feature_effects import CATALOG, OUTCOMES, frames, effect_matrix, feature_curve, controls
from src.features import branch_hour_panel, clock_template_check, hourly_profile, staffing_template
x = load_data()
fr = frames(x); e = fr['enriched']
print(f'{len(x):,} item lines, {x.transaction.nunique():,} baskets, {x.date.min():%d %b} – {x.date.max():%d %b %Y}')
print(f'{len(CATALOG)} engineered features; enriched table is {e.shape[0]:,} × {e.shape[1]}')
'''),
md('''
## 1. The feature catalog
Every engineered feature with its group, grain and a summary of its values across the 51,177 lines. No customer or transaction identifiers are shown.
'''),
code('''
def summarize(f):
    s = e[f]
    if pd.api.types.is_bool_dtype(s): return f'{s.mean():.1%} true'
    if pd.api.types.is_numeric_dtype(s): return f'{s.min():.3g} – {s.max():.3g} (median {s.median():.3g})'
    top = s.dropna().astype(str).value_counts()
    return f'{len(top)} values, top: {top.index[0]}' if len(top) else 'empty'
catalog = pd.DataFrame([dict(feature=f, group=g, grain=r, description=d,
    values=summarize(f) if f in e else '', missing=f'{e[f].isna().mean():.1%}' if f in e else '')
    for f, (g, r, d) in CATALOG.items()])
catalog
'''),
md('''
## 2. How an effect is measured
- **Contrast:** "on vs off" for flags; the 10th to the 90th percentile for numbers; one dummy per level for categories.
- **Raw:** slope across all baskets (or branch-days / branch-hours for demand), with no adjustment.
- **Controlled:** the same slope *within* cells of branch × month × clock hour (plus weekday for demand) × promotion window. This removes seasonality, branch size, time of day and the two 15% campaigns. Clock features are not controlled for themselves.
- **Uncertainty:** standard errors clustered by day; Benjamini–Hochberg q-values across all tests.
- **Replication:** the controlled effect must hold with |t| > 2 and the same sign in both Jan–Mar and Apr–Jun.
- **Units:** demand outcomes are % changes (log model). Shares are percentage points. Money is USD per basket.

Verdicts: **Replicated effect** · **Unreplicated** (significant overall, one half only) · **Confounded** (significant raw, gone after controls) · **No effect** · **Mechanical or selection** (true by definition, e.g. bigger baskets are more likely to contain a discount) · **Absorbed by controls**.
'''),
code('''
m = effect_matrix(fr)   # ~15 seconds
print(f'{len(m):,} feature × outcome tests'); m.verdict.value_counts().to_frame('tests')
'''),
md('## 3. Overview: verdicts by feature group'),
code('''
v = m.groupby(['group', 'verdict']).size().rename('tests').reset_index()
px.bar(v, y='group', x='tests', color='verdict', orientation='h', category_orders={'verdict': VERDICTS},
       color_discrete_map=COLORS, height=380, title='Only the clock produces replicated effects')
'''),
md('''
## 4. Heatmap: every feature × every outcome
Colour is the controlled t-statistic, capped at ±10. |t| < 2 is noise. Grey cells are definitional or untestable. Rows are sorted by their strongest signal.
'''),
code('''
heat = m.assign(signal=m.t.clip(-10, 10).where(~m.verdict.isin(['Mechanical or selection', 'Absorbed by controls'])))
grid = heat.pivot_table(index='feature', columns='outcome', values='signal', aggfunc='first')[[o for o in OUTCOMES if o in heat.outcome.unique()]]
grid = grid.reindex(heat.groupby('feature').signal.apply(lambda s: s.abs().max()).sort_values(ascending=False).index)
px.imshow(grid, color_continuous_scale=['#ae664d', '#f4efe8', '#547965'], zmin=-10, zmax=10, aspect='auto',
          height=max(500, 14*len(grid)), labels=dict(color='controlled t'), title='Controlled signal')
'''),
md('## 5. What actually has an effect'),
code('''
cols = ['feature', 'outcome_label', 'contrast', 'raw_effect', 'effect', 'ci_low', 'ci_high', 'unit', 'q', 'controls']
m[m.verdict.eq('Replicated effect')].sort_values('q')[cols].round(3)
'''),
md('''
## 6. What looks like an effect but isn't
These are significant raw and disappear after controls, usually because the feature tracks season, branch or time of day. Rainy days, for example, cluster in winter, when volume is lower anyway.
'''),
code('''
conf = m[m.verdict.eq('Confounded (raw only)')].assign(shrink=lambda d: d.effect - d.raw_effect)
conf.reindex(conf.raw_t.abs().sort_values(ascending=False).index)[cols[:8] + ['raw_q', 'q']].head(30).round(3)
'''),
md('''
## 7. Every feature, group by group
Forest plots: the controlled effect with its 95% interval for every feature in a group, one panel per outcome. A bar crossing zero means no detectable effect.
'''),
code('''
def forest(group):
    d = m[m.group.eq(group) & ~m.verdict.isin(['Mechanical or selection', 'Absorbed by controls'])].copy()
    if d.empty: return
    d['err_plus'] = d.ci_high - d.effect; d['err_minus'] = d.effect - d.ci_low
    fig = px.scatter(d, x='effect', y='feature', color='verdict', facet_col='outcome', facet_col_wrap=3,
                     error_x='err_plus', error_x_minus='err_minus', color_discrete_map=COLORS,
                     category_orders={'verdict': VERDICTS}, height=max(420, 26*d.feature.nunique()),
                     hover_data=['contrast', 'unit', 'raw_effect', 'q'], title=f'{group}: controlled effects (95% CI)')
    fig.update_xaxes(matches=None, zeroline=True, zerolinecolor='#888'); fig.for_each_annotation(lambda a: a.update(text=a.text.split('=')[-1]))
    fig.show()
for group in dict.fromkeys(g for g, _, _ in CATALOG.values()): forest(group)
'''),
md('''
## 8. Raw vs controlled curves for headline features
The terracotta line is raw and the green line is controlled. A slope that flattens once controls are applied means the feature was standing in for something else.
'''),
code('''
def curve(feature, outcome):
    frame = fr['daily'] if outcome == 'daily_baskets' else fr['hourly'] if outcome == 'hourly_baskets' else fr['basket']
    c = feature_curve(frame, feature, outcome, controls(feature, outcome))
    fig = px.line(c.melt(id_vars=['level', 'n'], value_vars=['raw', 'controlled'], var_name='view', value_name=outcome),
                  x='level', y=outcome, color='view', markers=True, hover_data=['n'], height=330,
                  color_discrete_map={'raw': '#ae664d', 'controlled': '#547965'},
                  title=f'{feature} → {OUTCOMES[outcome][1]}')
    fig.update_layout(xaxis_title=feature); fig.show()
for f, o in [('temp_mean', 'daily_baskets'), ('rainy', 'daily_baskets'), ('hour', 'dine_in'), ('hour', 'cold_share'),
             ('temp_band', 'cold_share'), ('weekday', 'daily_baskets'), ('dust_max', 'daily_baskets'),
             ('holiday', 'daily_baskets'), ('day_of_month', 'daily_baskets'), ('customer_visit_number', 'gp')]:
    curve(f, o)
'''),
md('''
## 9. Is anything left to find? The clock template and the noise floor
The template is branch × hour + weekday × hour + trend, fitted as a Poisson model on Jan–Apr and tested on May–Jun. *Dispersion* = 1 means the leftover variation is pure arrival randomness. The *Poisson floor* is the error a perfect model would still make.
'''),
code('''
g = branch_hour_panel(x)
clock_template_check(g).round(3)
'''),
code('''
hp = hourly_profile(x).melt(id_vars=['hour', 'baskets'], var_name='measure', value_name='share')
px.line(hp, x='hour', y='share', color='measure', markers=True, height=330,
        title='Dine-in steps at 18:00; cold-drink share steps at 11:00 and 19:00, in every month and branch').update_yaxes(tickformat='.0%')
'''),
code('''
st_ = staffing_template(g, x)
st_.sort_values('expected', ascending=False).head(15).round(2)
'''),
md('''
## 10. Explore any feature yourself
Choose a feature and an outcome. This needs `ipywidgets`, which Colab includes. Without it, call `curve('feature', 'outcome')` directly.
'''),
code('''
try:
    import ipywidgets as w
    feat = w.Dropdown(options=list(CATALOG), value='rainy', description='Feature')
    outc = w.Dropdown(description='Outcome')
    def _sync(*_): outc.options = list(m[m.base_feature.eq(feat.value)].outcome.unique())
    feat.observe(_sync, 'value'); _sync()
    def show(feature, outcome):
        if outcome: curve(feature, outcome); display(m[m.base_feature.eq(feature) & m.outcome.eq(outcome)][cols + ['verdict']].round(3))
    display(w.interactive(show, feature=feat, outcome=outc))
except ImportError:
    print("ipywidgets not installed: use curve('rainy', 'daily_baskets')")
'''),
md('''
## 11. Conclusions
1. **Plan by the clock.** Hour and weekday explain demand, dine-in and drink mix. The template is within about 1% of the noise floor, so further features cannot improve forecasts by much.
2. **Don't plan by the weather.** No weather, dust, holiday, school-break or Ramadan feature survives controls, and most "effects" are season or time of day in disguise. Iced drinks are an evening occasion, not a heat response.
3. **The payday window** is the one non-clock signal (+~4–5% daily baskets). Retest it on new data before using it for rosters.
4. **Basket and customer features** mostly restate arithmetic (bigger baskets contain more discounts) or show nothing (repeat visitors spend the same).
5. **Data caveat.** Demand that is pure Poisson noise around a fixed template, plus formula prices and `SYN-` IDs, suggests a simulated file. Rerun this notebook on real POS data before acting.
'''),
]

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--execute', action='store_true'); a = p.parse_args()
    nb = nbf.v4.new_notebook(); nb.cells = CELLS
    nb.metadata.update(kernelspec=dict(name='python3', display_name='Python 3', language='python'),
                       colab=dict(provenance=[], toc_visible=True))
    OUT.parent.mkdir(exist_ok=True)
    if a.execute:
        from nbclient import NotebookClient
        NotebookClient(nb, timeout=600, kernel_name='python3', resources={'metadata': {'path': str(OUT.parent)}}).execute()
    nbf.write(nb, OUT); print('Wrote', OUT)
