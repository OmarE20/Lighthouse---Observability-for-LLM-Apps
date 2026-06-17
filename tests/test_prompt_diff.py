from lighthouse.capture.openai_wrapper import wrap_openai
from lighthouse.prompts import PromptTemplate, diff_prompt_versions

from .conftest import make_fake_openai_client


def test_prompt_versions_increment_and_diff_groups_runs_by_version(storage, emitter):
    client = wrap_openai(make_fake_openai_client(), storage, emitter)

    tmpl = PromptTemplate("summarize", storage)
    tmpl.new_version("Summarize this: {text}")
    v1 = tmpl.render(text="hello world")
    assert v1.version == 1

    client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": v1.text}],
        lighthouse_prompt_version_id=v1.prompt_version_id,
        lighthouse_prompt_inputs={"text": "hello world"},
    )

    tmpl.new_version("Summarize concisely: {text}")
    v2 = tmpl.render(text="hello world")
    assert v2.version == 2

    client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": v2.text}],
        lighthouse_prompt_version_id=v2.prompt_version_id,
        lighthouse_prompt_inputs={"text": "hello world"},
    )

    emitter.flush()
    diff = diff_prompt_versions(storage, "summarize", 1, 2)

    assert diff["version_a"]["template"] == "Summarize this: {text}"
    assert diff["version_b"]["template"] == "Summarize concisely: {text}"
    assert len(diff["runs_a"]) == 1
    assert len(diff["runs_b"]) == 1
    assert diff["runs_a"][0]["inputs"] == {"text": "hello world"}
