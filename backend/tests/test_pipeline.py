import json
import uuid

import pytest

import app.pipeline.runner as runner
from app.io import write_json
from app.tcga.client import InsufficientData


@pytest.mark.parametrize('error,status',[
    (InsufficientData('Insufficient data: no matched normals.'),'insufficient_data'),
    (ValueError('Public source could not be read.'),'failed'),
])
def test_pipeline_failure_is_persisted(tmp_path,monkeypatch,error,status):
    monkeypatch.setattr(runner,'RUNS',tmp_path)
    def unavailable():
        raise error
    monkeypatch.setattr(runner,'projects',unavailable)
    id=str(uuid.uuid4())
    folder=tmp_path/id
    folder.mkdir()
    write_json(folder/'state.json',{'id':id,'created_at':'2026-09-20T00:00:00Z','status':'queued'})
    runner.execute(id,{'cancer':'breast cancer'})
    state=json.loads((folder/'state.json').read_text())
    audit=json.loads((folder/'analysis_metadata.json').read_text())
    assert state['status']==status
    assert state['error']==str(error)
    assert audit['error']==str(error) and audit['failed_at']
    assert not (folder/'results.json').exists()
