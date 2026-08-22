"""Test E (determinismo)/J: costruzione dell'input del judge (prompt.py). Nessuna chiamata LLM."""

from tools.semantic_boundary.prompt import build_judge_input, render_judge_prompt
from tools.semantic_boundary.resolver import build_request

from tests.semantic_boundary.fixtures import make_candidate_dict, make_timeline


def _request():
    timeline = make_timeline([f"n{i}" for i in range(4)])
    candidate = make_candidate_dict(before_node_id="n1", after_node_id="n2")
    return build_request(candidate, timeline)


def test_build_judge_input_is_deterministic_for_identical_requests():
    assert build_judge_input(_request()) == build_judge_input(_request())


def test_build_judge_input_contains_no_chain_of_thought_instruction():
    payload = build_judge_input(_request())
    assert "chain-of-thought" in payload["task_instruction"].lower()
    assert "Do not include chain-of-thought" in payload["task_instruction"]


def test_render_judge_prompt_is_deterministic_text():
    assert render_judge_prompt(_request()) == render_judge_prompt(_request())


def test_render_judge_prompt_includes_context_and_evidence():
    text = render_judge_prompt(_request())
    assert "CONTEXT BEFORE:" in text
    assert "CONTEXT AFTER:" in text
    assert "M4.2A EVIDENCE" in text
