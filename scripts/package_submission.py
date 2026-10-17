"""Create a source/aggregate-only archive, excluding raw records and Git history."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
EXACT=['README.md','requirements.txt','.gitignore','app.py','database/build_database.py',
       'database/schema.sql','database/queries.sql','database/add_features.py',
       'database/features_schema.sql','database/feature_queries.sql','analysis/README.md','analysis/requirements.txt',
       'analysis/run_analysis.py','analysis/test_analysis.py','simulator/README.md']
TREES=['src','scripts','tests','reports','data','notebooks','analysis/outputs','simulator/dist','simulator/tests']

def build():
    files={ROOT/p for p in EXACT if (ROOT/p).is_file()}
    for directory in TREES:
        files.update(p for p in (ROOT/directory).rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.sqlite','.sql','.zip'])
    destination=ROOT/'dist/stories-coffee-source.zip';destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination,'w',ZIP_DEFLATED) as archive:
        for path in sorted(files): archive.write(path,path.relative_to(ROOT))
    with ZipFile(destination) as archive:
        names=archive.namelist()
        assert not any(n.startswith(('.git/','reference/','.venv/')) or n.endswith(('.sqlite','.docx')) or
            n in ['stories_transactions.csv','stories_transactions_enriched.csv','database/stories.sql'] for n in names)
        assert archive.testzip() is None
    print(f'{destination}: {len(files)} files; raw records and Git history excluded')

if __name__=='__main__':build()
