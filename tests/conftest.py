import sys
import types

import pytest

from lighthouse.capture.emitter import Emitter
from lighthouse.storage.backend import Storage


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test.db"
    return Storage(f"sqlite:///{db_path}")


@pytest.fixture
def emitter(storage):
    e = Emitter(storage)
    yield e
    e.flush()


def make_fake_openai_client(responses=None):
    """Build a minimal fake OpenAI client exposing client.chat.completions.create,
    shaped like the real SDK's response object, so wrap_openai can be tested
    without network access or the real openai package installed.
    """

    class Usage:
        def __init__(self, prompt_tokens, completion_tokens):
            self.prompt_tokens = prompt_tokens
            self.completion_tokens = completion_tokens

    class Message:
        def __init__(self, content):
            self.content = content

    class Choice:
        def __init__(self, content):
            self.message = Message(content)

    class Response:
        def __init__(self, content="hello", prompt_tokens=10, completion_tokens=5):
            self.choices = [Choice(content)]
            self.usage = Usage(prompt_tokens, completion_tokens)

    call_log = []

    def create(*args, **kwargs):
        call_log.append(kwargs)
        if responses == "raise":
            raise RuntimeError("simulated API error")
        return Response()

    completions = types.SimpleNamespace(create=create)
    chat = types.SimpleNamespace(completions=completions)
    client = types.SimpleNamespace(chat=chat, _call_log=call_log)
    return client


def make_fake_anthropic_client():
    class Usage:
        def __init__(self, input_tokens, output_tokens):
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens

    class Block:
        def __init__(self, text):
            self.text = text

    class Response:
        def __init__(self, text="hello", input_tokens=8, output_tokens=4):
            self.content = [Block(text)]
            self.usage = Usage(input_tokens, output_tokens)

    call_log = []

    def create(*args, **kwargs):
        call_log.append(kwargs)
        return Response()

    messages = types.SimpleNamespace(create=create)
    client = types.SimpleNamespace(messages=messages, _call_log=call_log)
    return client
