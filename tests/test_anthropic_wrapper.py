from lighthouse.capture.anthropic_wrapper import wrap_anthropic

from .conftest import make_fake_anthropic_client


def test_anthropic_call_is_captured_with_correct_tokens_and_cost(storage, emitter):
    client = wrap_anthropic(make_fake_anthropic_client(), storage, emitter)

    response = client.messages.create(
        model="claude-sonnet-4-6", messages=[{"role": "user", "content": "hi"}], max_tokens=100
    )
    assert response.content[0].text == "hello"

    emitter.flush()
    calls = storage.list_calls(limit=10)
    assert len(calls) == 1
    c = calls[0]
    assert c.provider == "anthropic"
    assert c.input_tokens == 8
    assert c.output_tokens == 4
    assert c.cost_usd > 0
