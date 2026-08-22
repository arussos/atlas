"""Test E (determinismo)/J: costruzione dell'input del judge (prompt.py). Nessuna chiamata LLM."""

from tools.semantic_boundary.prompt import TASK_INSTRUCTION, build_judge_input, render_judge_prompt
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


# M4.2b-C — TASK_INSTRUCTION v0.2 semantic invariants (prompt-only change).
# These tests check that the instruction text itself contains the required
# invariants; they do not depend on any Gold Pilot record or expected
# judge decision (no Gold tuning per docs §M4.2b-C).


def test_v0_2_same_project_does_not_imply_same_episode():
    text = TASK_INSTRUCTION.lower()
    assert "the same project" in text
    assert "none of the above is sufficient on its own to decide same_episode" in text


def test_v0_2_same_broad_topic_does_not_imply_same_episode():
    text = TASK_INSTRUCTION.lower()
    assert "the same broad topic" in text


def test_v0_2_new_work_unit_can_be_boundary_inside_same_project():
    text = TASK_INSTRUCTION.lower()
    assert "even inside the same project, customer, system, or topic" in text
    assert "even if it belongs to the same project" in text


def test_v0_2_ordinary_continuation_and_substeps_remain_same_episode():
    text = TASK_INSTRUCTION.lower()
    for phrase in [
        "a new substep of the same work unit",
        "question -> answer",
        "implementation -> review",
        "implementation -> test",
        "test -> fix -> retest",
        "debugging of the same problem",
        "correction of the same deliverable",
        "a new tool or strategy for the same problem",
        "an ordinary immediate follow-up of the same work unit",
    ]:
        assert phrase in text


def test_v0_2_candidate_score_is_explicitly_not_a_probability():
    assert "candidate_score is a Boundary Evidence Score" in TASK_INSTRUCTION
    assert "It is NOT a probability of BOUNDARY" in TASK_INSTRUCTION


def test_v0_2_candidate_score_is_explicitly_not_semantic_confidence():
    assert "NOT a semantic confidence" in TASK_INSTRUCTION
    assert "NOT a target value for your confidence" in TASK_INSTRUCTION


def test_v0_2_judge_confidence_must_not_be_derived_from_candidate_score():
    text = TASK_INSTRUCTION.lower()
    assert "do not copy candidate_score into your confidence" in text
    assert "do not derive your confidence from it mathematically" in text
    assert "reflect only how reliable you consider your own" in text


def test_v0_2_uncertain_remains_available_for_insufficient_semantic_evidence():
    text = TASK_INSTRUCTION.lower()
    assert "uncertain" in text
    assert (
        "does not allow a semantically reliable distinction between "
        "same_episode and boundary" in text
    )


def test_v0_2_task_instruction_contains_no_gold_pilot_ids():
    text = TASK_INSTRUCTION.upper()
    assert "GOLD-" not in text
