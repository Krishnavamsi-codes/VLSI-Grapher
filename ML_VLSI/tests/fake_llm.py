"""Test doubles for the LLM layer: nothing here touches the network."""
import json
import types

import llm_client
from llm_client import LLMClient, LLMConfig, LLMError, LLMResult


class FakeLLM:
    """Stands in for LLMClient. `script` is a list of callables or results consumed per create() call:
    a dict -> parsed JSON answer; a list of (name, args) -> function calls; an Exception -> raised."""

    def __init__(self, script=None, available=True, model='fake-model', default=None):
        self.config = LLMConfig(api_key='sk-test-FAKEKEY-0123456789abcdef', model=model)
        self.available = available
        self.reason = None if available else 'fake unavailable'
        self.script = list(script or [])
        self.default = default
        self.calls = []

    @property
    def model(self):
        return self.config.model

    def status(self):
        return {'available': self.available, 'model': self.model, 'reason': None if self.available else self.reason}

    def probe(self):
        return self.available

    def create(self, **kwargs):
        self.calls.append(kwargs)
        step = self.script.pop(0) if self.script else self.default
        if callable(step) and not isinstance(step, (dict, list)):
            step = step(kwargs)
        if isinstance(step, Exception):
            raise step
        usage = {'input_tokens': 100, 'cached_tokens': 0, 'output_tokens': 20, 'reasoning_tokens': 0, 'cost_usd': 0.0004}
        if isinstance(step, list):
            calls = [{'call_id': f'call_{i}_{len(self.calls)}', 'name': n, 'arguments': a} for i, (n, a) in enumerate(step)]
            items = [{'type': 'function_call', 'call_id': c['call_id'], 'name': c['name'],
                      'arguments': json.dumps(c['arguments'])} for c in calls]
            return LLMResult(text='', parsed=None, function_calls=calls, output_items=items, usage=usage, latency_ms=1)
        if step is None:
            raise AssertionError('FakeLLM script exhausted')
        return LLMResult(text=json.dumps(step), parsed=step, function_calls=[], output_items=[], usage=usage,
                         latency_ms=1)

    def payload_text(self):
        """Everything ever sent to the model, as one string."""
        return json.dumps([{k: v for k, v in c.items() if k in ('instructions', 'input')} for c in self.calls],
                          default=str)


# ---------------------------------------------------------------------------
# Fake OpenAI SDK objects (for testing LLMClient itself)
# ---------------------------------------------------------------------------

class _Obj(types.SimpleNamespace):
    def model_dump(self, exclude_none=False):
        return {k: v for k, v in vars(self).items() if not (exclude_none and v is None)}


def sdk_response(text=None, calls=(), status='completed', refusal=None, incomplete_reason=None):
    output = []
    for c in calls:
        output.append(_Obj(type='function_call', call_id=c['call_id'], name=c['name'],
                           arguments=json.dumps(c['arguments'])))
    if text is not None or refusal is not None:
        content = [{'type': 'refusal', 'refusal': refusal}] if refusal else [{'type': 'output_text', 'text': text}]
        output.append(_Obj(type='message', role='assistant', content=content))
    usage = types.SimpleNamespace(input_tokens=1000, output_tokens=200, total_tokens=1200,
                                  input_tokens_details=types.SimpleNamespace(cached_tokens=100, cache_write_tokens=0),
                                  output_tokens_details=types.SimpleNamespace(reasoning_tokens=50))
    return types.SimpleNamespace(status=status, output=output, usage=usage,
                                 incomplete_details=types.SimpleNamespace(reason=incomplete_reason))


class FakeSDK:
    """Mimics openai.OpenAI().responses.create with a script of responses/exceptions."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def make_client(script, key='sk-test-SECRETKEY-abcdef0123456789', model='gpt-6-sol'):
    logs = []
    cfg = LLMConfig(api_key=key, model=model, prices=dict(llm_client.PRICES.get(model, {})))
    client = LLMClient(config=cfg, sdk_client=FakeSDK(script), sleep=lambda s: None, log=logs.append)
    return client, logs


def openai_error(kind, key_in_message=''):
    """Build a real openai exception instance of the given kind."""
    import httpx2 as httpx
    import openai
    req = httpx.Request('POST', 'https://api.openai.com/v1/responses')
    msg = f'error {key_in_message}'.strip()
    if kind == 'timeout':
        return openai.APITimeoutError(request=req)
    if kind == 'connection':
        return openai.APIConnectionError(request=req)
    code = {'auth': 401, 'notfound': 404, 'rate': 429, 'quota': 429, 'server': 500, 'bad': 400}[kind]
    cls = {'auth': openai.AuthenticationError, 'notfound': openai.NotFoundError, 'rate': openai.RateLimitError,
           'quota': openai.RateLimitError, 'server': openai.InternalServerError, 'bad': openai.BadRequestError}[kind]
    body = {'type': 'insufficient_quota', 'code': 'credit_balance_exhausted', 'message': msg} if kind == 'quota' else None
    return cls(msg, response=httpx.Response(code, request=req), body=body)
