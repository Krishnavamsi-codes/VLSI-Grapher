import glob
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from circuit_store import DATASET_DIR  # noqa: E402

BENCHMARKS = sorted(glob.glob(os.path.join(DATASET_DIR, '*.v')))
CSV_PATH = os.path.join(ROOT, 'GNN-RE', 'GraphSAINT', 'predictions_all_nodes.csv')


def pytest_configure(config):
    config.addinivalue_line('markers', 'slow: full 37-file fault matrix (set RUN_SLOW=1)')


def pytest_collection_modifyitems(config, items):
    if os.environ.get('RUN_SLOW') == '1':
        return
    skip = pytest.mark.skip(reason='slow; set RUN_SLOW=1 to run')
    for item in items:
        if 'slow' in item.keywords:
            item.add_marker(skip)


def bench_id(path):
    return os.path.basename(path).replace('_Syn_65nm.v', '')
