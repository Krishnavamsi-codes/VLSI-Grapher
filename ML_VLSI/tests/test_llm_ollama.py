"""Local provider (Ollama) path of LLMClient: config, request shape, the tools + schema split, errors.
The SDK is always faked: nothing here touches the network or a running Ollama."""
import json

import pytest

import assistant as asst
import llm_client
from analysis_service import AnalysisService
from circuit_store import resolve_circuit
from fake_llm import FakeLLM, FakeSDK, make_client, openai_error, sdk_response
from llm_client import LLMClient, LLMConfig, LOCAL_API_KEY

BASE_URL = 'http://localhost:11434/v1'
MODEL = 'qwen2.5:3b'
SUM_CALL = {'call_id': 'c1', 'name': 'add_numbers', 'arguments': {'a': 2, 'b': 3}}
ENV_KEYS = ('OPENAI_API_KEY', 'OPENAI_TIMEOUT', 'OPENAI_MODEL', 'OPENAI_BASE_URL', 'OPENAI_SEND_REASONING',
            'OPENAI_REASONING_EFFORT_REPORT', 'OPENAI_REASONING_EFFORT_CHAT')


def make_local_client(script):
    logs = []
    cfg = LLMConfig(api_key=LOCAL_API_KEY, model=MODEL, base_url=BASE_URL, send_reasoning=False)
    client = LLMClient(config=cfg, sdk_client=FakeSDK(script), sleep=lambda s: None, log=logs.append)
    return client, logs


def _create(client, **kw):
    args = dict(purpose='test', instructions='x', input=[{'role': 'user', 'content': 'q'}],
                schema=LLMClient.PROBE_SCHEMA, schema_name='probe', tools=[LLMClient.PROBE_TOOL], effort='low')
    args.update(kw)
    return client.create(**args)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_env(monkeypatch):
    for k in ENV_KEYS:
        monkeypatch.delenv(k, raising=False)


def test_load_config_local_needs_no_key_and_skips_reasoning(tmp_path, clean_env):
    env = tmp_path / '.env'
    env.write_text(f'OPENAI_BASE_URL={BASE_URL}\nOPENAI_MODEL={MODEL}\n')
    cfg = llm_client.load_config(str(env))
    assert cfg.base_url == BASE_URL and cfg.model == MODEL
    assert cfg.api_key == LOCAL_API_KEY and cfg.send_reasoning is False
    assert cfg.prices == {}
    assert BASE_URL in repr(cfg)


def test_load_config_local_reasoning_can_be_turned_on(tmp_path, clean_env):
    env = tmp_path / '.env'
    env.write_text(f'OPENAI_BASE_URL={BASE_URL}\nOPENAI_MODEL=qwen3:8b\nOPENAI_SEND_REASONING=1\n')
    assert llm_client.load_config(str(env)).send_reasoning is True


def test_load_config_openai_defaults_unchanged(tmp_path, clean_env):
    env = tmp_path / '.env'
    env.write_text('OPENAI_MODEL=gpt-6-sol\n')
    cfg = llm_client.load_config(str(env))
    assert cfg.base_url == '' and cfg.api_key == '' and cfg.send_reasoning is True
    assert 'base_url' not in repr(cfg)


def test_real_sdk_client_points_at_local_server():
    cfg = LLMConfig(api_key=LOCAL_API_KEY, model=MODEL, base_url=BASE_URL, send_reasoning=False)
    client = LLMClient(config=cfg, log=lambda *_: None)   # builds openai.OpenAI; no request is made
    assert str(client._sdk.base_url).rstrip('/') == BASE_URL


# ---------------------------------------------------------------------------
# Tools + schema split
# ---------------------------------------------------------------------------

def test_split_returns_tool_calls_from_tools_only_request():
    client, _ = make_local_client([sdk_response(calls=[SUM_CALL])])
    res = _create(client)
    assert res.function_calls == [SUM_CALL] and res.parsed is None
    (req,) = client._sdk.calls
    assert req['tools'] == [LLMClient.PROBE_TOOL]
    assert 'text' not in req and 'reasoning' not in req


def test_split_asks_for_schema_when_model_answers_without_tools():
    client, _ = make_local_client([sdk_response(text='The sum is 5.'), sdk_response(text='{"sum": 5}')])
    res = _create(client)
    assert res.parsed == {'sum': 5} and res.function_calls == []
    first, second = client._sdk.calls
    assert 'text' not in first and first['tools']
    assert 'tools' not in second and 'tool_choice' not in second
    assert second['text']['format']['schema'] == LLMClient.PROBE_SCHEMA
    assert second['input'] == [{'role': 'user', 'content': 'q'}, {'role': 'assistant', 'content': 'The sum is 5.'}]
    assert 'reasoning' not in second


def test_split_adds_no_draft_when_first_answer_is_empty():
    client, _ = make_local_client([sdk_response(text=''), sdk_response(text='{"sum": 5}')])
    _create(client)
    assert client._sdk.calls[1]['input'] == [{'role': 'user', 'content': 'q'}]


def test_split_sums_usage_and_latency_of_both_steps():
    client, logs = make_local_client([sdk_response(text='5'), sdk_response(text='{"sum": 5}')])
    res = _create(client)
    assert res.usage == {'input_tokens': 2000, 'cached_tokens': 200, 'output_tokens': 400,
                         'reasoning_tokens': 100, 'cost_usd': None}
    assert len([l for l in logs if 'purpose=test' in l]) == 2


def test_split_tool_choice_none_goes_straight_to_schema():
    client, _ = make_local_client([sdk_response(text='{"sum": 5}')])
    res = _create(client, tool_choice='none')
    assert res.parsed == {'sum': 5}
    (req,) = client._sdk.calls
    assert 'tools' not in req and 'tool_choice' not in req and 'text' in req


def test_split_required_without_call_does_not_ask_for_schema():
    client, _ = make_local_client([sdk_response(text='5')])
    res = _create(client, tool_choice='required')
    assert res.function_calls == [] and res.parsed is None
    assert len(client._sdk.calls) == 1


@pytest.mark.parametrize('kw, key', [({'tools': None}, 'text'), ({'schema': None}, 'tools')])
def test_local_single_feature_requests_are_not_split(kw, key):
    reply = sdk_response(text='{"sum": 5}') if key == 'text' else sdk_response(calls=[SUM_CALL])
    client, _ = make_local_client([reply])
    _create(client, **kw)
    (req,) = client._sdk.calls
    assert key in req and 'reasoning' not in req


def test_openai_path_still_sends_tools_and_schema_together():
    client, _ = make_client([sdk_response(calls=[SUM_CALL])])
    _create(client, tool_choice='required')
    (req,) = client._sdk.calls
    assert req['tools'] and req['text']['format']['strict'] is True
    assert req['tool_choice'] == 'required' and req['reasoning'] == {'effort': 'low'}


# ---------------------------------------------------------------------------
# Draft preservation (step B must not rewrite the tool-grounded reply)
# ---------------------------------------------------------------------------

HIGHLIGHTS = {'gate_ids': [23, 5], 'nets': ['Result_add[12]'], 'finding_ids': [], 'edges': []}
DRAFT = 'Result_add[12] is driven by [G23] pin S and read by [G5] pin A.'


def _chat_create(client, **kw):
    return _create(client, schema=asst.CHAT_SCHEMA, schema_name='chat_reply', tools=asst.TOOLS, **kw)


def test_split_keeps_draft_as_reply_and_takes_highlights_from_schema_step():
    garbled = {'reply': 'No findings for this net yet.', 'highlights': HIGHLIGHTS}
    client, _ = make_local_client([sdk_response(text=DRAFT), sdk_response(text=json.dumps(garbled))])
    res = _chat_create(client)
    assert res.parsed == {'reply': DRAFT, 'highlights': HIGHLIGHTS}
    assert json.loads(res.text) == res.parsed and res.function_calls == []
    assert client._sdk.calls[1]['input'][-1] == {'role': 'assistant', 'content': DRAFT}


def test_split_keeps_backslash_net_names_verbatim():
    draft = 'The net \\adder_1/intadd_0/n4 is driven by [G23] and read by [G22].'
    mangled = {'reply': 'The net \\\nadder_1/intadd_0/n4 is driven by [G23].', 'highlights': HIGHLIGHTS}
    client, _ = make_local_client([sdk_response(text='  ' + draft + '\n'), sdk_response(text=json.dumps(mangled))])
    assert _chat_create(client).parsed['reply'] == draft


def test_split_uses_schema_reply_when_there_is_no_draft():
    answer = {'reply': 'From the schema step.', 'highlights': HIGHLIGHTS}
    client, _ = make_local_client([sdk_response(text='   '), sdk_response(text=json.dumps(answer))])
    assert _chat_create(client).parsed == answer


def test_split_tool_choice_none_uses_schema_reply():
    answer = {'reply': 'Answer with what you have.', 'highlights': HIGHLIGHTS}
    client, _ = make_local_client([sdk_response(text=json.dumps(answer))])
    assert _chat_create(client, tool_choice='none').parsed == answer
    assert len(client._sdk.calls) == 1


def test_split_invalid_schema_json_keeps_the_draft_with_empty_metadata():
    client, logs = make_local_client([sdk_response(text=DRAFT), sdk_response(text='{"reply": "x", "highl')])
    res = _chat_create(client)
    assert res.parsed == {'reply': DRAFT, 'highlights': {'gate_ids': [], 'nets': [], 'finding_ids': [], 'edges': []}}
    assert any('schema step failed' in l for l in logs)


def test_split_invalid_schema_json_still_fails_without_a_draft():
    client, _ = make_local_client([sdk_response(text=''), sdk_response(text='{"reply": "x", "highl')])
    with pytest.raises(llm_client.LLMError) as exc:
        _chat_create(client)
    assert exc.value.kind == 'schema'


def test_split_schema_without_reply_field_is_unchanged():
    client, _ = make_local_client([sdk_response(text='The sum is 5.'), sdk_response(text='{"sum": 5}')])
    res = _create(client)
    assert res.parsed == {'sum': 5} and res.text == '{"sum": 5}'


# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------

def test_local_requests_send_low_temperature():
    client, _ = make_local_client([sdk_response(text=DRAFT), sdk_response(text=json.dumps(
        {'reply': 'x', 'highlights': HIGHLIGHTS})), sdk_response(text='{"sum": 5}')])
    _chat_create(client)                     # split: step A + step B
    _create(client, tools=None)              # single schema-only call
    assert [c.get('temperature') for c in client._sdk.calls] == [0.1, 0.1, 0.1]
    assert llm_client.LOCAL_TEMPERATURE == 0.1


def test_openai_requests_send_no_temperature_and_keep_shape():
    garbled = {'reply': 'schema reply', 'highlights': HIGHLIGHTS}
    client, _ = make_client([sdk_response(text=json.dumps(garbled))])
    res = _chat_create(client)
    (req,) = client._sdk.calls
    assert 'temperature' not in req
    assert set(req) == {'model', 'instructions', 'input', 'store', 'include', 'reasoning', 'text', 'tools'}
    assert res.parsed == garbled             # no draft handling on the OpenAI path


def test_probe_passes_on_local_server():
    client, _ = make_local_client([sdk_response(calls=[SUM_CALL]),
                                   sdk_response(text='The result is 5.'), sdk_response(text='{"sum": 5}')])
    assert client.probe() and client.status() == {'available': True, 'model': MODEL, 'reason': None}
    calls = client._sdk.calls
    assert len(calls) == 3
    assert 'text' not in calls[0] and 'text' not in calls[1] and 'tools' not in calls[2]
    assert {'type': 'function_call_output', 'call_id': 'c1', 'output': '{"result": 5}'} in calls[1]['input']
    assert not any('reasoning' in c for c in calls)


def test_probe_reports_model_that_never_calls_tools():
    client, _ = make_local_client([sdk_response(text='{"sum": 5}')])
    assert client.probe() is False
    assert 'did not call the strict test tool' in client.status()['reason']


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('script, expected, attempts', [
    ([openai_error('connection'), openai_error('connection')], f'local LLM server at {BASE_URL}', 2),
    ([openai_error('notfound')], f'ollama pull {MODEL}', 1),
    ([openai_error('timeout')], 'timed out after 60 s', 1),
])
def test_local_errors_are_clear(script, expected, attempts):
    client, _ = make_local_client(script)
    assert client.probe() is False
    assert expected in client.status()['reason']
    assert len(client._sdk.calls) == attempts


# ---------------------------------------------------------------------------
# Chat loop through the real Assistant (assistant.py unchanged)
# ---------------------------------------------------------------------------

def test_chat_tool_loop_works_through_split():
    answer = {'reply': 'Step-B rewrite that must not reach the user.',
              'highlights': {'gate_ids': [0], 'nets': [], 'finding_ids': [], 'edges': []}}
    client, _ = make_local_client([
        sdk_response(calls=[{'call_id': 'c1', 'name': 'get_gate', 'arguments': {'gate_id': 0}}]),
        sdk_response(text='Gate [G0] is shown.'),
        sdk_response(text=json.dumps(answer)),
    ])
    client._set_status(True, None)
    a = asst.Assistant(client, AnalysisService(FakeLLM(available=False), lambda m: [2] * m['num_gates']))
    out = a.chat(None, resolve_circuit('Demo_cut_carry__Validate_add_mul_8_bit_Syn_65nm.v'), 'What does gate 0 do?')
    assert out['reply'] == 'Gate [G0] is shown.' and out['highlights']['gate_ids'] == [0]
    # 'gate 0' is looked up automatically before the first model call; the model's own call follows
    assert [(t['tool'], t.get('auto', False)) for t in out['tool_trace']] == [('get_gate', True), ('get_gate', False)]
    assert all(t['ok'] for t in out['tool_trace'])
    first, second, third = client._sdk.calls
    assert any(i.get('type') == 'function_call_output' and i['call_id'] == 'auto_0' for i in first['input'])
    assert 'text' not in first and 'text' not in second and 'tools' not in third
    assert any(i.get('type') == 'function_call_output' and i['call_id'] == 'c1' for i in second['input'])
    assert out['usage']['input_tokens'] == 3000


def test_local_timeout_defaults_longer_and_is_configurable(tmp_path, clean_env, monkeypatch):
    env = tmp_path / '.env'
    env.write_text(f'OPENAI_BASE_URL={BASE_URL}\nOPENAI_MODEL={MODEL}\n')
    assert llm_client.load_config(str(env)).timeout == llm_client.LOCAL_TIMEOUT_S
    env.write_text('OPENAI_MODEL=gpt-6-sol\n')
    assert llm_client.load_config(str(env)).timeout == llm_client.DEFAULT_TIMEOUT_S == 60.0
    monkeypatch.setenv('OPENAI_TIMEOUT', '240')
    env.write_text(f'OPENAI_BASE_URL={BASE_URL}\nOPENAI_MODEL={MODEL}\n')
    assert llm_client.load_config(str(env)).timeout == 240.0
