import hashlib
import json
import logging
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import httpx
from filelock import FileLock

log = logging.getLogger('iris')

def now():
    return datetime.now(timezone.utc).isoformat()

def write_json(path, value):
    path = Path(path)
    content = json.dumps(value, indent=2, allow_nan=False)
    # Each writer needs its own temporary file when catalog requests overlap.
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(content)
            stream.close()
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)

def digest(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def request_json(url, params=None):
    for attempt in range(4):
        try:
            with httpx.Client(timeout=httpx.Timeout(90, connect=20), follow_redirects=True) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)

def download(url, path, expected_md5=None):
    path = Path(path)
    manifest = path.with_suffix(path.suffix + '.source.json')
    with FileLock(str(path) + '.lock', timeout=600):
        if path.exists() and manifest.exists():
            meta = json.loads(manifest.read_text())
            if digest(path) == meta['sha256'] and (not expected_md5 or digest(path, 'md5') == expected_md5):
                return meta
        temp = path.with_suffix(path.suffix + '.part')
        for attempt in range(4):
            try:
                with httpx.Client(timeout=httpx.Timeout(180, connect=25), follow_redirects=True) as client:
                    with client.stream('GET', url) as response:
                        response.raise_for_status()
                        with temp.open('wb') as out:
                            for chunk in response.iter_bytes(1024 * 1024):
                                out.write(chunk)
                if not temp.stat().st_size:
                    raise ValueError('Downloaded file is empty')
                if expected_md5 and digest(temp, 'md5') != expected_md5:
                    raise ValueError('GDC checksum mismatch')
                meta = dict(url=url, downloaded_at=now(), bytes=temp.stat().st_size,
                            sha256=digest(temp), expected_md5=expected_md5)
                temp.replace(path)
                write_json(manifest, meta)
                return meta
            except (httpx.HTTPError, ValueError):
                log.exception('Download attempt %s failed: %s', attempt + 1, url)
                if attempt == 3:
                    temp.unlink(missing_ok=True)
                    raise
                time.sleep(2 ** attempt)
