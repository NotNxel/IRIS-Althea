import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
import pytest
from app.io import digest, download, write_json

def test_verified_cache_reuse_and_checksum(tmp_path,monkeypatch):
    path=tmp_path/'data.tsv';path.write_text('actual test bytes\n')
    meta={'url':'https://example.invalid/file','sha256':digest(path),'bytes':path.stat().st_size}
    write_json(path.with_suffix('.tsv.source.json'),meta)
    monkeypatch.setattr('app.io.httpx.Client',lambda **kwargs:pytest.fail('Valid cache should avoid network'))
    assert download(meta['url'],path,expected_md5=digest(path,'md5'))==meta

def test_atomic_json_rejects_nonfinite(tmp_path):
    path=tmp_path/'state.json';write_json(path,{'status':'queued'})
    with pytest.raises(ValueError):write_json(path,{'score':float('nan')})
    assert json.loads(path.read_text())=={'status':'queued'}


def test_concurrent_json_writers_use_separate_temporary_files(tmp_path,monkeypatch):
    barrier=Barrier(8)
    replace=Path.replace
    def replace_together(source,target):
        barrier.wait(timeout=10)
        return replace(source,target)
    monkeypatch.setattr(Path,'replace',replace_together)
    path=tmp_path/'projects.json'
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda index:write_json(path,{'writer':index}),range(8)))
    assert json.loads(path.read_text())['writer'] in range(8)
    assert list(tmp_path.glob('*.tmp'))==[]
