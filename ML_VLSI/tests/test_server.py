"""HTTP routes: explicit routes only, traversal rejected, upload flow, error JSON."""
import http.client
import http.server
import json
import threading

import pytest

import circuit_store


@pytest.fixture(scope='module')
def server():
    import web_dashboard
    srv = web_dashboard.make_server('127.0.0.1', 0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def _request(srv, method, path, body=None, raw_body=None):
    conn = http.client.HTTPConnection('127.0.0.1', srv.server_address[1], timeout=60)
    headers = {}
    data = raw_body
    if body is not None:
        data = json.dumps(body).encode('utf-8')
    if data is not None:
        headers['Content-Type'] = 'application/json'
    conn.request(method, path, body=data, headers=headers)
    resp = conn.getresponse()
    payload = resp.read()
    conn.close()
    try:
        parsed = json.loads(payload)
    except ValueError:
        parsed = None
    return resp.status, payload, parsed, resp.getheader('Content-Type')


def test_server_config():
    import web_dashboard
    assert web_dashboard.HOST == '127.0.0.1'
    assert issubclass(web_dashboard.RequestHandler, http.server.BaseHTTPRequestHandler)
    assert not issubclass(web_dashboard.RequestHandler, http.server.SimpleHTTPRequestHandler)


@pytest.mark.parametrize('path', [
    '/.env', '/%2eenv', '/%2Eenv', '/./.env', '//.env', '/static/.env', '/static/%2eenv',
    '/web_dashboard.py', '/GNN-RE/GraphSAINT/predictions_all_nodes.csv',
    '/static/../.env', '/static/%2e%2e/.env', '/static/%2E%2E/.env', '/static/%2e%2e%2f.env',
    '/static/..%2f.env', '/static/..%5c.env', '/static/%252e%252e/.env', '/static/....//.env',
    '/static/../web_dashboard.py', '/static/', '/static/nope.css', '/static/dashboard.py',
    '/static/%00.css', '/static/C:%5cWindows%5cwin.ini',
])
def test_unknown_and_traversal_paths_are_404(server, path):
    status, payload, parsed, _ = _request(server, 'GET', path)
    assert status == 404
    assert parsed == {'error_code': 'NOT_FOUND', 'message': 'Not found.'}
    assert b'OPENAI' not in payload


def test_static_whitelisted_file_is_served(server):
    status, payload, _, ctype = _request(server, 'GET', '/static/dashboard.css')
    assert status == 200 and ctype.startswith('text/css') and b'glass-card' in payload


@pytest.mark.parametrize('name', ['../../../.env', '..%2F..%2F.env', 'C:%5CWindows%5Cwin.ini',
                                  '%2Fetc%2Fpasswd', '..', '.'])
def test_load_circuit_rejects_traversal(server, name):
    status, _, parsed, _ = _request(server, 'GET', '/api/load_circuit?name=' + name)
    assert status == 400 and parsed['error_code'] == 'INVALID_CIRCUIT_NAME'


@pytest.mark.parametrize('body, code', [
    ({'circuit_name': '../.env'}, 'INVALID_CIRCUIT_NAME'),
    ({'circuit_name': '../../web_dashboard.py'}, 'INVALID_CIRCUIT_NAME'),
    ({'upload_id': '../../../.env'}, 'INVALID_UPLOAD_ID'),
    ({'upload_id': 'ABC'}, 'INVALID_UPLOAD_ID'),
    ({}, 'MISSING_CIRCUIT'),
])
def test_infer_rejects_bad_references(server, body, code):
    status, _, parsed, _ = _request(server, 'POST', '/api/infer', body)
    assert status == 400 and parsed['error_code'] == code


def test_unknown_circuit_is_404(server):
    status, _, parsed, _ = _request(server, 'POST', '/api/infer', {'circuit_name': 'Nope.v'})
    assert status == 404 and parsed['error_code'] == 'CIRCUIT_NOT_FOUND'


def test_bad_json_is_400(server):
    status, _, parsed, _ = _request(server, 'POST', '/api/infer', raw_body=b'{not json')
    assert status == 400 and parsed['error_code'] == 'INVALID_JSON'


def test_circuit_listing_has_demo_group_and_no_uploads(server):
    status, _, parsed, _ = _request(server, 'GET', '/api/circuits')
    assert status == 200
    assert len(parsed['circuits']) == 37
    assert len(parsed['demo_circuits']) == 3
    assert not any('Upload' in c for c in parsed['circuits'] + parsed['demo_circuits'])


def test_benchmark_infer(server):
    status, _, parsed, _ = _request(server, 'POST', '/api/infer',
                                    {'circuit_name': 'Test_add_mul_16_bit_Syn_65nm.v'})
    assert status == 200
    assert parsed['gnn_re_available'] is True and parsed['prediction_source'] == 'graphsaint'
    assert len(parsed['predictions']) == 863
    m = parsed['metrics']
    assert m['precision'] != m['f1_macro'] or m['recall'] != m['f1_macro'] or m['f1_macro'] == 1.0


def test_demo_infer_uses_base_predictions(server):
    demo = circuit_store.list_demos()[0]
    status, _, parsed, _ = _request(server, 'POST', '/api/infer', {'circuit_name': demo})
    assert status == 200 and parsed['gnn_re_available'] is True
    assert 'unfaulted base circuit' in parsed['gnn_re_message']


def test_upload_flow_and_na_metrics(server):
    with open(circuit_store.os.path.join(circuit_store.DATASET_DIR, 'Train_add_mul_4_bit_Syn_65nm.v')) as f:
        content = f.read()
    status, _, up, _ = _request(server, 'POST', '/api/upload_circuit', {'filename': 'x.v', 'content': content})
    assert status == 200 and len(up['upload_id']) == 32 and len(up['nodes']) == 79
    try:
        status, _, parsed, _ = _request(server, 'POST', '/api/infer', {'upload_id': up['upload_id']})
        assert status == 200
        assert parsed['metrics'] is None and parsed['gnn_re_available'] is False
        assert parsed['gnn_re_message'].startswith('N/A: no GraphSAINT prediction for uploads')
        assert parsed['prediction_source'] == 'baseline' and len(parsed['predictions']) == 79
        status, _, loaded, _ = _request(server, 'GET', '/api/load_circuit?upload_id=' + up['upload_id'])
        assert status == 200 and loaded['source'] == 'upload'
        # uploads never appear in the benchmark dropdown
        _, _, listing, _ = _request(server, 'GET', '/api/circuits')
        assert up['upload_id'] + '.v' not in listing['circuits']
    finally:
        circuit_store.delete_upload(up['upload_id'])


@pytest.mark.parametrize('content', ['not verilog at all', 'module m (a); input a; endmodule'])
def test_invalid_upload_returns_error_json(server, content):
    status, _, parsed, _ = _request(server, 'POST', '/api/upload_circuit', {'filename': 'bad.v', 'content': content})
    assert status == 400 and parsed['error_code'] == 'INVALID_NETLIST'


def test_oversized_upload_is_413(server):
    content = 'a' * (circuit_store.MAX_UPLOAD_BYTES + 1)
    status, _, parsed, _ = _request(server, 'POST', '/api/upload_circuit', {'filename': 'big.v', 'content': content})
    assert status == 413 and parsed['error_code'] == 'UPLOAD_TOO_LARGE'
