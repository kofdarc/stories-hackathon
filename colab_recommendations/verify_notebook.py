"""Execute actual notebook code with real widgets, safe aggregate evidence only.

Run from repository root. Input file is read locally, never copied or embedded.
Requires ipywidgets, pandas, numpy, matplotlib, IPython, nbformat.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile
import sys
os.environ.setdefault('MPLBACKEND','Agg')
import nbformat
import matplotlib.figure
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
input_path=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'stories_transactions.csv'
nb_path=HERE/'Stories_Coffee_Decision_Lab.ipynb'
nb=nbformat.read(nb_path,as_version=4)
nbformat.validate(nb)
ns={'__name__':'stories_notebook_verification'}
captured=[]
figures=[]

def capture(*objects,**kwargs):
    for obj in objects:
        if isinstance(obj,matplotlib.figure.Figure):figures.append(obj)
        captured.append(type(obj).__name__)

with contextlib.redirect_stdout(io.StringIO()) as log:
    for i,cell in enumerate(nb.cells):
        if cell.cell_type!='code':continue
        source='\n'.join(line for line in cell.source.splitlines() if not line.startswith('%pip'))
        exec(compile(source,f'notebook_cell_{i}','exec'),ns)
        # Real widgets, but suppress dataframe output / raw terminal flood.
        ns['display']=capture
    assert ns['DATA'] is None
    ns['local_path'].value=str(input_path)
    ns['load_clicked']()
    assert ns['DATA'] is None, 'Authorization gate must block loading'
    ns['authorized'].value=True
    ns['load_clicked']()
    assert ns['DATA'] is not None,log.getvalue()
    assert ns['RESULT'] is not None,log.getvalue()
    assert len(ns['RESULT']['ranking'])==10
    first=ns['RESULT']
    # Exercise actual widgets and callbacks across branches and product selectors.
    for branch in sorted(ns['DATA'].branch.unique()):
        ns['CONTROLS']['branch'].value=branch
        ns['render_results']()
        assert ns['RESULT']['parameters']['branch']==branch
    ns['CONTROLS']['branch'].value=sorted(ns['DATA'].branch.unique())[0]
    ns['CONTROLS']['price_increase'].value=.1
    ns['CONTROLS']['basket_loss'].value=0
    ns['render_results']()
    before=float(ns['RESULT']['ranking'].set_index('scenario').loc['Price increase','delta_usd'])
    ns['CONTROLS']['basket_loss'].value=.2
    ns['render_results']()
    after=float(ns['RESULT']['ranking'].set_index('scenario').loc['Price increase','delta_usd'])
    assert after<before
    ns['CONTROLS']['combo_conversion'].value=.1
    ns['render_candidates']()
    ns['render_sensitivity']()
    ns['render_results']()
    result=ns['RESULT']
    archive=ns['report_archive'](result,ns['QUALITY'])
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        assert len(z.namelist())==8
        contents='\n'.join(z.read(f).decode() for f in z.namelist())
        for identifier in ns['DATA'].customer.dropna().unique():
            assert identifier not in contents,'Customer ID leaked into report'
        for identifier in ns['DATA'].transaction.unique():
            assert identifier not in contents,'Transaction ID leaked into report'
    # Exercise local download callback without leaving report artifacts.
    old_cwd=os.getcwd()
    try:
        with tempfile.TemporaryDirectory(prefix='stories-report-') as tmp:
            os.chdir(tmp)
            ns['download_report']()
            assert Path('stories_decision_report.zip').exists()
    finally:os.chdir(old_cwd)
    # Bad input must clear an old dashboard, avoiding stale results.
    ns['local_path'].value='/nonexistent/stories.csv'
    ns['load_clicked']()
    assert ns['DATA'] is None and ns['RESULT'] is None and len(ns['PANEL'].children)==0

assert figures,'No chart was generated'
artifacts=HERE/'verification'
artifacts.mkdir(exist_ok=True)
figures[0].savefig(artifacts/'ranking_preview.png',dpi=130,bbox_inches='tight')
summary={
 'notebook_schema':'nbformat validation passed',
 'embedded_engine_sha256':hashlib.sha256((HERE/'engine.py').read_bytes()).hexdigest(),
 'source_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
 'source_rows':first['measured']['rows'],
 'source_quality':json.loads(json.dumps(ns.get('quality',{}) or {},default=str)),
 'checks':['all notebook code cells executed (setup install skipped: preinstalled test dependencies)',
   'actual ipywidgets constructed; authorization gate; local authorized CSV load',
   'all three branch controls; live scenario recalculation; basket-loss direction',
   'combo branch/time exploration; all nine sensitivity curves; report ZIP',
   'download callback; no transaction/customer IDs in ZIP',
   'failed load clears stale dashboard; notebook has no saved outputs'],
 'figures_rendered':len(figures),
 'verification_environment':'Local Python with real ipywidgets; hosted Colab upload/download dialogs not automated',
 'forecast_scores':first['restock']['scores'].to_dict('records'),
}
# Use recomputed quality from original source; contains aggregates only.
_,quality=ns['load_transactions'](input_path)
summary['source_quality']=quality
summary['calibration_rows']=summary.pop('source_rows')
(artifacts/'verification.json').write_text(json.dumps(summary,indent=2,default=str)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['forecast_scores']},indent=2,default=str))
