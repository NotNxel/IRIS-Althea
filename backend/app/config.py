import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get('IRIS_DATA_DIR', ROOT / 'data')).resolve()
CACHE = DATA / 'cache'
RUNS = DATA / 'analyses'
for path in [CACHE, RUNS]:
    path.mkdir(parents=True, exist_ok=True)
VERSION = '0.1.0'
GDC = 'https://api.gdc.cancer.gov'
