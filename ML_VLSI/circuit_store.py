"""
circuit_store.py - Single place where circuit references are resolved to files.

Every API route that touches a netlist goes through resolve_circuit(), which
guarantees the resolved path stays inside one of three allowed directories:

    benchmark : GNN-RE/.../Interconnected-Modules/*.v   (read-only dataset)
    demo      : demo_faults/*.v                          (fault-injected copies)
    upload    : uploads/<32-hex-id>.v                    (user uploads)
"""

import glob
import hashlib
import json
import os
import re
import threading
import uuid
import zipfile
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(HERE, 'GNN-RE', 'Netlist_to_graph', 'Circuits_datasets', 'Interconnected-Modules')
DATASET_ARCHIVE = os.path.join(HERE, 'GNN-RE', 'Netlist_to_graph.zip')
DEMO_DIR = os.path.join(HERE, 'demo_faults')
DEMO_MANIFEST = os.path.join(DEMO_DIR, 'manifest.json')
UPLOAD_DIR = os.path.join(HERE, 'uploads')

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_STORED_UPLOADS = 100
_UPLOAD_ID_RE = re.compile(r'^[0-9a-f]{32}$')
_upload_lock = threading.Lock()
_dataset_lock = threading.Lock()

# kind: 'benchmark' | 'demo' | 'upload'
# key:  stable identifier used for caching ('benchmark:<file>', 'upload:<id>', ...)
# csv_key: circuit_file name in predictions_all_nodes.csv, or None
CircuitRef = namedtuple('CircuitRef', 'kind key path display_name csv_key')


class CircuitRefError(ValueError):
    def __init__(self, status, error_code, message):
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.message = message


def _ensure_benchmark_dataset():
    """Unpack the upstream benchmark archive when a fresh submodule has no data."""
    if os.path.isdir(DATASET_DIR):
        return
    with _dataset_lock:
        if os.path.isdir(DATASET_DIR):
            return
        if not os.path.isfile(DATASET_ARCHIVE):
            return
        extract_root = os.path.join(HERE, 'GNN-RE')
        root_real = os.path.realpath(extract_root)
        with zipfile.ZipFile(DATASET_ARCHIVE) as archive:
            for member in archive.infolist():
                target = os.path.realpath(os.path.join(extract_root, member.filename))
                if os.path.commonpath([root_real, target]) != root_real:
                    raise CircuitRefError(500, 'INVALID_DATASET_ARCHIVE', 'Benchmark archive contains an unsafe path.')
            archive.extractall(extract_root)


def is_inside(base, rel):
    """True if base/rel resolves (symlinks included) to a path inside base."""
    base_real = os.path.realpath(base)
    path = os.path.realpath(os.path.join(base_real, rel))
    try:
        return os.path.commonpath([path, base_real]) == base_real and path != base_real
    except ValueError:   # different drives on Windows
        return False


def check_upload_size(content):
    if not isinstance(content, str):
        raise CircuitRefError(400, 'INVALID_UPLOAD', 'Upload content must be text.')
    if len(content.encode('utf-8')) > MAX_UPLOAD_BYTES:
        raise CircuitRefError(413, 'UPLOAD_TOO_LARGE',
                              f'Upload exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.')


def _inside(base, name):
    """Resolve base/name and require the result to be a file inside base."""
    if not isinstance(name, str) or not name or name != os.path.basename(name) or name in ('.', '..'):
        raise CircuitRefError(400, 'INVALID_CIRCUIT_NAME', 'Invalid circuit name.')
    if not is_inside(base, name):
        raise CircuitRefError(400, 'INVALID_CIRCUIT_NAME', 'Invalid circuit name.')
    path = os.path.realpath(os.path.join(os.path.realpath(base), name))
    if not os.path.isfile(path):
        raise CircuitRefError(404, 'CIRCUIT_NOT_FOUND', f'Circuit {name!r} not found.')
    return path


def list_benchmarks():
    _ensure_benchmark_dataset()
    return sorted(os.path.basename(f) for f in glob.glob(os.path.join(DATASET_DIR, '*.v')))


def _demo_manifest():
    if not os.path.exists(DEMO_MANIFEST):
        return {}
    with open(DEMO_MANIFEST, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_demos():
    manifest = _demo_manifest()
    return sorted(os.path.basename(f) for f in glob.glob(os.path.join(DEMO_DIR, '*.v'))
                  if os.path.basename(f) in manifest)


def resolve_circuit(circuit_name=None, upload_id=None):
    """Return a CircuitRef for a benchmark/demo filename or an upload id."""
    if upload_id is not None:
        if not isinstance(upload_id, str) or not _UPLOAD_ID_RE.match(upload_id):
            raise CircuitRefError(400, 'INVALID_UPLOAD_ID', 'Invalid upload id.')
        path = _inside(UPLOAD_DIR, upload_id + '.v')
        return CircuitRef('upload', 'upload:' + upload_id, path, 'Uploaded netlist', None)

    if not circuit_name:
        raise CircuitRefError(400, 'MISSING_CIRCUIT', 'Provide circuit_name or upload_id.')
    if circuit_name in list_benchmarks():
        path = _inside(DATASET_DIR, circuit_name)
        return CircuitRef('benchmark', 'benchmark:' + circuit_name, path, circuit_name, circuit_name)
    manifest = _demo_manifest()
    if circuit_name in manifest:
        path = _inside(DEMO_DIR, circuit_name)
        # Faults preserve gate count/order, so the base circuit's predictions still align.
        return CircuitRef('demo', 'demo:' + circuit_name, path, circuit_name, manifest[circuit_name]['base'])
    # Run the path check anyway so traversal attempts get 400, not 404.
    _inside(DATASET_DIR, circuit_name)
    raise CircuitRefError(404, 'CIRCUIT_NOT_FOUND', f'Circuit {circuit_name!r} not found.')


def save_upload(content):
    """Store uploaded netlist text under a fresh id. Returns the id."""
    check_upload_size(content)
    data = content.encode('utf-8')
    upload_id = uuid.uuid4().hex
    with _upload_lock:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(os.path.join(UPLOAD_DIR, upload_id + '.v'), 'wb') as f:
            f.write(data)
        _prune_uploads()
    return upload_id


def delete_upload(upload_id):
    if _UPLOAD_ID_RE.match(upload_id or ''):
        try:
            os.remove(os.path.join(UPLOAD_DIR, upload_id + '.v'))
        except OSError:
            pass


def _prune_uploads():
    files = sorted(glob.glob(os.path.join(UPLOAD_DIR, '*.v')), key=os.path.getmtime)
    for old in files[:-MAX_STORED_UPLOADS]:
        try:
            os.remove(old)
        except OSError:
            pass


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()
