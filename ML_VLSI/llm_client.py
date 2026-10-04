"""
llm_client.py - The one place that talks to OpenAI (Responses API).

All assistant code calls LLMClient.create(); tests inject a fake SDK client (or a
fake LLMClient) so nothing touches the network.

Guarantees:
  * The API key is read from ML_VLSI/.env (python-dotenv) or the environment and is
    never printed, logged or returned. Every error message passes through _sanitize().
  * 60 s timeout (180 s for a local server; OPENAI_TIMEOUT overrides), one retry (with backoff) on 429 / 5xx / connection errors.
  * Refusals, incomplete and failed responses raise LLMError with a clear message.
  * Token usage, estimated cost and latency are logged to stdout per request.
  * store=False: prompts and outputs are not stored by OpenAI; encrypted reasoning
    items are requested so multi-step tool loops can pass them back.

Local provider (Ollama): set OPENAI_BASE_URL (e.g. http://localhost:11434/v1) and
OPENAI_MODEL (e.g. qwen2.5:3b). Ollama serves the same Responses API, so the request
and response shapes are unchanged. Differences handled here, only when OPENAI_BASE_URL
is set:
  * no API key needed (a placeholder is used);
  * `reasoning` is not sent (non-thinking models reject it; OPENAI_SEND_REASONING=1
    turns it back on);
  * Ollama enforces the JSON schema as a grammar, which stops the model from calling
    tools when both are sent, and it ignores tool_choice. create() therefore splits such
    calls: tools only first, then the schema only if the model answered instead of
    calling a tool (see _create_split). The tools-step answer is kept verbatim as the
    schema's `reply` field; the schema step only supplies the other fields;
  * temperature is fixed at LOCAL_TEMPERATURE so answers are repeatable.
"""

import dataclasses
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field

from dotenv import dotenv_values

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, '.env')

DEFAULT_TIMEOUT_S = 60.0
LOCAL_TIMEOUT_S = 180.0          # OPENAI_BASE_URL set; override either with OPENAI_TIMEOUT
RETRY_BACKOFF_S = 2.0
LOCAL_API_KEY = 'local-no-key'   # placeholder: local servers ignore the key, the SDK requires one
LOCAL_TEMPERATURE = 0.1          # local path only; the OpenAI path sends no temperature
DRAFT_FIELD = 'reply'            # schema field that keeps the tools-step draft verbatim (split calls only)

# USD per 1M tokens, standard tier, short context. Source: developers.openai.com/api/docs/pricing
# (retrieved 2026-09-27). Override with OPENAI_PRICE_INPUT / _CACHED_INPUT / _OUTPUT.
PRICES = {
    'gpt-6-astra': {'input': 10.00, 'cached_input': 1.00, 'output': 50.00},
    'gpt-6-sol':   {'input': 2.00,  'cached_input': 0.20, 'output': 10.00},
    'gpt-6-luna':  {'input': 0.10,  'cached_input': 0.01, 'output': 0.50},
}


class LLMError(Exception):
    """A call failed. `message` is safe to show to users (no key, no raw payload)."""

    def __init__(self, message, kind='error', retryable=False):
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.retryable = retryable


@dataclass
class LLMConfig:
    api_key: str = ''
    model: str = ''
    effort_report: str = 'medium'
    effort_chat: str = 'low'
    timeout: float = DEFAULT_TIMEOUT_S
    prices: dict = field(default_factory=dict)
    base_url: str = ''            # set -> local OpenAI-compatible server (Ollama)
    send_reasoning: bool = True

    def __repr__(self):  # never show the key
        local = f', base_url={self.base_url!r}' if self.base_url else ''
        return f'LLMConfig(model={self.model!r}, api_key={"<set>" if self.api_key else "<missing>"}{local})'


def load_config(env_path=ENV_PATH):
    values = {k: v for k, v in dotenv_values(env_path).items() if v is not None} if os.path.exists(env_path) else {}

    def get(name, default=''):
        return os.environ.get(name) or values.get(name) or default

    model = get('OPENAI_MODEL').strip()
    prices = dict(PRICES.get(model, {}))
    for key, env in (('input', 'OPENAI_PRICE_INPUT'), ('cached_input', 'OPENAI_PRICE_CACHED_INPUT'),
                     ('output', 'OPENAI_PRICE_OUTPUT')):
        if get(env):
            prices[key] = float(get(env))
    base_url = get('OPENAI_BASE_URL').strip()
    reasoning = get('OPENAI_SEND_REASONING').strip().lower()
    # a local model shares the GPU with whatever else runs on the machine, so it gets a longer default timeout
    try:
        timeout = float(get('OPENAI_TIMEOUT') or (LOCAL_TIMEOUT_S if base_url else DEFAULT_TIMEOUT_S))
    except ValueError:
        timeout = LOCAL_TIMEOUT_S if base_url else DEFAULT_TIMEOUT_S
    return LLMConfig(api_key=get('OPENAI_API_KEY').strip() or (LOCAL_API_KEY if base_url else ''), model=model,
                     timeout=timeout,
                     effort_report=get('OPENAI_REASONING_EFFORT_REPORT', 'medium').strip(),
                     effort_chat=get('OPENAI_REASONING_EFFORT_CHAT', 'low').strip(),
                     prices=prices, base_url=base_url,
                     send_reasoning=reasoning in ('1', 'true', 'yes') if reasoning else not base_url)


@dataclass
class LLMResult:
    text: str
    parsed: object            # parsed JSON when a schema was requested, else None
    function_calls: list      # [{'call_id', 'name', 'arguments' (dict)}]
    output_items: list        # raw output items (dicts) to pass back as input in tool loops
    usage: dict
    latency_ms: float


def _sanitize(text, key):
    text = str(text)
    if key:
        text = text.replace(key, '<redacted>')
    text = re.sub(r'sk-[A-Za-z0-9_\-]{8,}', 'sk-<redacted>', text)
    return text[:500]


def _skeleton(schema):
    """The smallest value that satisfies a JSON schema (required keys, empty arrays/strings)."""
    t = schema.get('type')
    if isinstance(t, list):
        return None if 'null' in t else _skeleton(dict(schema, type=t[0]))
    if t == 'object':
        return {k: _skeleton(v) for k, v in schema.get('properties', {}).items() if k in schema.get('required', [])}
    if t == 'array':
        return []
    if t == 'string':
        return schema['enum'][0] if schema.get('enum') else ''
    if t in ('integer', 'number'):
        return 0
    return False if t == 'boolean' else None


def _add_usage(a, b):
    out = {k: (a.get(k) or 0) + (b.get(k) or 0)
           for k in ('input_tokens', 'cached_tokens', 'output_tokens', 'reasoning_tokens')}
    costs = [u['cost_usd'] for u in (a, b) if u.get('cost_usd') is not None]
    out['cost_usd'] = round(sum(costs), 6) if costs else None
    return out


class LLMClient:
    """Thin wrapper around openai.OpenAI().responses.create()."""

    def __init__(self, config=None, sdk_client=None, sleep=time.sleep, log=print):
        self.config = config or load_config()
        self._sdk = sdk_client
        self._sleep = sleep
        self._log = log
        self._lock = threading.Lock()
        self.available = False
        self.reason = 'not checked yet'
        if self._sdk is None and self.config.api_key:
            import openai
            extra = {'base_url': self.config.base_url} if self.config.base_url else {}
            self._sdk = openai.OpenAI(api_key=self.config.api_key, timeout=self.config.timeout, max_retries=0,
                                      **extra)

    @property
    def model(self):
        return self.config.model

    def status(self):
        with self._lock:
            return {'available': self.available, 'model': self.config.model or None,
                    'reason': None if self.available else self.reason}

    def _set_status(self, available, reason):
        with self._lock:
            self.available, self.reason = available, reason

    # ------------------------------------------------------------------
    def create(self, *, purpose, instructions, input, schema=None, schema_name='output', tools=None,
               tool_choice=None, effort=None, max_output_tokens=None):
        if not self.config.api_key:
            raise LLMError('OPENAI_API_KEY is not set in ML_VLSI/.env', kind='config')
        if not self.config.model:
            raise LLMError('OPENAI_MODEL is not set in ML_VLSI/.env', kind='config')
        if self.config.base_url and tools and schema is not None:
            return self._create_split(purpose, instructions, input, schema, schema_name, tools, tool_choice,
                                      effort, max_output_tokens)
        return self._create_once(purpose, instructions, input, schema, schema_name, tools, tool_choice,
                                 effort, max_output_tokens)

    def _create_split(self, purpose, instructions, input, schema, schema_name, tools, tool_choice, effort,
                      max_output_tokens):
        """Local servers only: the schema grammar would block tool calls, so send tools and schema separately.
        Step 1 offers the tools (skipped for tool_choice='none'). If the model calls tools, those calls are
        returned as usual. Otherwise step 2 asks for the schema-shaped answer, with the model's step-1 text
        as a draft. If the schema has a string DRAFT_FIELD, the draft is kept verbatim there: step 2 only
        fills the other fields, because rewriting the draft into JSON lost or garbled tool-grounded facts.
        The caller sees one result with the usage of both steps."""
        first, draft = None, []
        if tool_choice != 'none':
            first = self._create_once(purpose, instructions, input, None, schema_name, tools, tool_choice,
                                      effort, max_output_tokens)
            if first.function_calls or tool_choice == 'required':
                return first
            if first.text.strip():
                draft = [{'role': 'assistant', 'content': first.text}]
        keeps_draft = bool(draft) and (schema.get('properties') or {}).get(DRAFT_FIELD, {}).get('type') == 'string'
        try:
            second = self._create_once(purpose, instructions, list(input) + draft, schema, schema_name, None, None,
                                       effort, max_output_tokens)
        except LLMError as err:
            # the draft is the answer; the schema step only adds metadata, so its failure must not lose the answer
            if not (keeps_draft and err.kind in ('schema', 'incomplete')):
                raise
            self._log(f'[llm] purpose={purpose} schema step failed ({err.kind}); keeping the draft, empty metadata')
            parsed = dict(_skeleton(schema), **{DRAFT_FIELD: first.text.strip()})
            return dataclasses.replace(first, parsed=parsed, text=json.dumps(parsed))
        if first is None:
            return second
        if keeps_draft:
            parsed = dict(second.parsed, **{DRAFT_FIELD: first.text.strip()})
            second = dataclasses.replace(second, parsed=parsed, text=json.dumps(parsed))
        return dataclasses.replace(second, usage=_add_usage(first.usage, second.usage),
                                   latency_ms=round(first.latency_ms + second.latency_ms, 1))

    def _create_once(self, purpose, instructions, input, schema, schema_name, tools, tool_choice, effort,
                     max_output_tokens):
        kwargs = {
            'model': self.config.model,
            'instructions': instructions,
            'input': input,
            'store': False,
            'include': ['reasoning.encrypted_content'],
        }
        if self.config.base_url:
            kwargs['temperature'] = LOCAL_TEMPERATURE
        if effort and self.config.send_reasoning:
            kwargs['reasoning'] = {'effort': effort}
        if schema is not None:
            kwargs['text'] = {'format': {'type': 'json_schema', 'name': schema_name, 'schema': schema, 'strict': True}}
        if tools:
            kwargs['tools'] = tools
        if tool_choice:
            kwargs['tool_choice'] = tool_choice
        if max_output_tokens:
            kwargs['max_output_tokens'] = max_output_tokens

        attempts = 2
        for attempt in range(1, attempts + 1):
            t0 = time.time()
            try:
                response = self._sdk.responses.create(**kwargs)
                break
            except Exception as exc:  # map SDK errors to safe messages
                err = self._map_error(exc)
                self._log(f'[llm] purpose={purpose} model={self.config.model} attempt={attempt} '
                          f'error={err.kind}: {err.message}')
                if err.retryable and attempt < attempts:
                    self._sleep(RETRY_BACKOFF_S * attempt)
                    continue
                raise err
        latency = (time.time() - t0) * 1000
        return self._parse(response, purpose, schema is not None, latency)

    def _map_error(self, exc):
        import openai
        key = self.config.api_key
        msg = _sanitize(getattr(exc, 'message', None) or exc, key)
        if isinstance(exc, openai.APITimeoutError):
            return LLMError(f'OpenAI request timed out after {self.config.timeout:.0f} s', kind='timeout')
        if self.config.base_url and isinstance(exc, openai.APIConnectionError):
            return LLMError(f'Could not connect to the local LLM server at {self.config.base_url} '
                            '(is Ollama running?)', kind='network', retryable=True)
        if self.config.base_url and isinstance(exc, openai.NotFoundError):
            return LLMError(f'Model {self.config.model!r} was not found on the local LLM server '
                            f'(try: ollama pull {self.config.model})', kind='model')
        if isinstance(exc, openai.APIConnectionError):
            return LLMError('Could not connect to the OpenAI API (network error)', kind='network', retryable=True)
        if isinstance(exc, openai.AuthenticationError):
            return LLMError('OpenAI rejected the API key (authentication failed)', kind='auth')
        if isinstance(exc, openai.PermissionDeniedError):
            return LLMError(f'Access to model {self.config.model!r} is not permitted for this key', kind='permission')
        if isinstance(exc, openai.NotFoundError):
            return LLMError(f'Model {self.config.model!r} was not found or is not available to this key',
                            kind='model')
        if isinstance(exc, openai.RateLimitError):
            if getattr(exc, 'type', None) == 'insufficient_quota' or getattr(exc, 'code', None) in (
                    'insufficient_quota', 'credit_balance_exhausted'):
                return LLMError('The OpenAI account has no credits remaining (insufficient_quota); add credits '
                                'in the OpenAI billing settings', kind='quota')
            return LLMError('OpenAI rate limit exceeded (HTTP 429)', kind='rate_limit', retryable=True)
        if isinstance(exc, openai.BadRequestError):
            return LLMError(f'OpenAI rejected the request: {msg}', kind='bad_request')
        if isinstance(exc, openai.APIStatusError):
            code = getattr(exc, 'status_code', 0) or 0
            return LLMError(f'OpenAI server error (HTTP {code})', kind='server', retryable=code >= 500)
        return LLMError(f'Unexpected OpenAI client error: {type(exc).__name__}', kind='error')

    def _parse(self, response, purpose, want_json, latency):
        status = getattr(response, 'status', None)
        if status == 'incomplete':
            reason = getattr(getattr(response, 'incomplete_details', None), 'reason', None) or 'unknown'
            raise LLMError(f'The model response was incomplete ({reason})', kind='incomplete')
        if status in ('failed', 'cancelled'):
            raise LLMError(f'The model response {status}', kind='failed')

        text_parts, calls, items = [], [], []
        for item in response.output or []:
            d = item.model_dump(exclude_none=True) if hasattr(item, 'model_dump') else dict(item)
            items.append(d)
            if d.get('type') == 'function_call':
                try:
                    args = json.loads(d.get('arguments') or '{}')
                except ValueError:
                    args = {'_invalid_json': d.get('arguments')}
                calls.append({'call_id': d['call_id'], 'name': d['name'], 'arguments': args})
            elif d.get('type') == 'message':
                for c in d.get('content', []):
                    if c.get('type') == 'refusal':
                        raise LLMError(f'The model refused: {_sanitize(c.get("refusal", ""), self.config.api_key)}',
                                       kind='refusal')
                    if c.get('type') == 'output_text':
                        text_parts.append(c.get('text', ''))
        text = ''.join(text_parts)

        usage = self._usage(response)
        self._log(f'[llm] purpose={purpose} model={self.config.model} in={usage["input_tokens"]} '
                  f'cached={usage["cached_tokens"]} out={usage["output_tokens"]} '
                  f'reasoning={usage["reasoning_tokens"]} cost_usd={usage["cost_usd"]} latency_ms={latency:.0f}')

        parsed = None
        if want_json and not calls:
            try:
                parsed = json.loads(text)
            except ValueError:
                raise LLMError('The model returned output that does not match the required JSON schema',
                               kind='schema')
            if not isinstance(parsed, dict):
                raise LLMError('The model returned output that does not match the required JSON schema',
                               kind='schema')
        return LLMResult(text=text, parsed=parsed, function_calls=calls, output_items=items,
                         usage=usage, latency_ms=round(latency, 1))

    def _usage(self, response):
        u = getattr(response, 'usage', None)
        get = lambda obj, name: getattr(obj, name, 0) or 0 if obj is not None else 0
        inp, out = get(u, 'input_tokens'), get(u, 'output_tokens')
        cached = get(getattr(u, 'input_tokens_details', None), 'cached_tokens')
        reasoning = get(getattr(u, 'output_tokens_details', None), 'reasoning_tokens')
        p = self.config.prices
        cost = None
        if {'input', 'cached_input', 'output'} <= set(p):
            cost = round(((inp - cached) * p['input'] + cached * p['cached_input'] + out * p['output']) / 1e6, 6)
        return {'input_tokens': inp, 'cached_tokens': cached, 'output_tokens': out,
                'reasoning_tokens': reasoning, 'cost_usd': cost}

    # ------------------------------------------------------------------
    PROBE_TOOL = {
        'type': 'function', 'name': 'add_numbers', 'strict': True,
        'description': 'Add two integers.',
        'parameters': {'type': 'object', 'additionalProperties': False, 'required': ['a', 'b'],
                       'properties': {'a': {'type': 'integer'}, 'b': {'type': 'integer'}}},
    }
    PROBE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['sum'],
                    'properties': {'sum': {'type': 'integer'}}}

    def probe(self):
        """Exercise a strict tool call, its round trip and a strict schema. Sets availability."""
        try:
            first = self.create(purpose='probe', instructions='Use the tool, then report the result.',
                                input=[{'role': 'user', 'content': 'What is 2 + 3? Call add_numbers.'}],
                                tools=[self.PROBE_TOOL], tool_choice='required', schema=self.PROBE_SCHEMA,
                                schema_name='probe', effort='low', max_output_tokens=2000)
            if not first.function_calls:
                raise LLMError('Model did not call the strict test tool (function calling unsupported?)',
                               kind='unsupported')
            call = first.function_calls[0]
            outputs = [{'type': 'function_call_output', 'call_id': call['call_id'],
                        'output': json.dumps({'result': 5})}]
            second = self.create(purpose='probe', instructions='Report the tool result.',
                                 input=[{'role': 'user', 'content': 'What is 2 + 3? Call add_numbers.'}]
                                 + first.output_items + outputs,
                                 tools=[self.PROBE_TOOL], schema=self.PROBE_SCHEMA, schema_name='probe',
                                 effort='low', max_output_tokens=2000)
            if not isinstance(second.parsed, dict) or second.parsed.get('sum') != 5:
                raise LLMError('Model output did not follow the strict JSON schema', kind='unsupported')
        except LLMError as err:
            self._set_status(False, err.message)
            return False
        self._set_status(True, None)
        return True
