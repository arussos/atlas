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


# M4.2b-E — TASK_INSTRUCTION v0.3 two-stage semantic procedure invariants.
# As for v0.2, these tests check the instruction text (and the payload
# contract) only; they encode no Gold Pilot record, ID, or expected judge
# decision. The two stages are a reasoning structure inside ONE judge
# request — no second model call exists anywhere to test.


def test_v0_3_stage_1_identifies_before_and_after_work_units():
    # Invariant A: explicit, independent identification of both work units.
    text = TASK_INSTRUCTION
    assert "STAGE 1" in text
    assert "identify independently" in text
    assert "the BEFORE work unit" in text
    assert "the AFTER work unit" in text
    lower = text.lower()
    assert "concrete work or deliverable being pursued in context before" in lower
    assert "concrete work or deliverable being pursued in context after" in lower


def test_v0_3_comparison_happens_after_identification():
    # Invariant B: STAGE 2 compares only after STAGE 1 identified both units.
    text = TASK_INSTRUCTION
    assert "STAGE 2" in text
    assert "Only after both work units are identified" in text
    assert text.index("STAGE 1") < text.index("STAGE 2")


def test_v0_3_same_project_topic_system_insufficient_for_same_episode():
    # Invariant C: shared project/topic/system context never decides SAME.
    lower = TASK_INSTRUCTION.lower()
    assert "what does not, by itself, imply same_episode" in lower
    assert "none of the above is sufficient on its own to decide same_episode" in lower
    assert "whether the two identified work units share the" in lower


def test_v0_3_tool_substep_method_change_insufficient_for_boundary():
    # Invariant D: tool/method/substep changes serving the same work unit
    # are explicitly insufficient for BOUNDARY.
    lower = TASK_INSTRUCTION.lower()
    assert "what does not, by itself, imply boundary" in lower
    assert (
        "a change of tool, implementation method, substep, perspective, or "
        "intermediate artifact" in lower
    )
    assert "serves the same immediate operational work unit" in lower


def test_v0_3_continuation_forms_remain_same_episode():
    # Invariant E: implementation/review/test/debug/fix/follow-up stay SAME.
    lower = TASK_INSTRUCTION.lower()
    assert (
        "continues, implements, reviews, tests, debugs, corrects, clarifies, "
        "or immediately follows up the same operational work unit" in lower
    )


def test_v0_3_materially_different_goal_can_be_boundary():
    # Invariant F: a materially different immediate goal/problem/deliverable
    # can be BOUNDARY even inside the same project.
    lower = TASK_INSTRUCTION.lower()
    assert "begins a materially different operational work unit" in lower
    assert "with a different immediate goal, problem, or deliverable" in lower


def test_v0_3_uncertain_covers_unidentifiable_work_units():
    # Invariant G: UNCERTAIN remains available when the two work units
    # cannot be identified or compared reliably.
    lower = TASK_INSTRUCTION.lower()
    assert (
        "does not allow the two operational work units to be identified or "
        "compared reliably" in lower
    )


def test_v0_3_candidate_score_anti_anchoring_preserved():
    # Invariant H: the v0.2 anti-anchoring section survives v0.3 verbatim.
    assert "candidate_score is a Boundary Evidence Score" in TASK_INSTRUCTION
    assert "It is NOT a probability of BOUNDARY" in TASK_INSTRUCTION
    assert "NOT a target value for your confidence" in TASK_INSTRUCTION
    lower = TASK_INSTRUCTION.lower()
    assert "do not copy candidate_score into your confidence" in lower
    assert "do not derive your confidence from it mathematically" in lower


def test_v0_3_work_units_are_internal_scaffolding_never_output():
    # Invariant I (instruction side): work units never appear in the output.
    lower = TASK_INSTRUCTION.lower()
    assert "internal reasoning scaffolding only" in lower
    assert "never add them, or any other field, to the output" in lower
    assert "return only a structured decision" in lower
    assert "Do not include chain-of-thought" in TASK_INSTRUCTION


def test_v0_3_judge_payload_contract_has_no_work_unit_fields():
    # Invariant I (payload side): the externally visible contract is
    # unchanged — no before_work_unit/after_work_unit anywhere.
    payload = build_judge_input(_request())
    assert set(payload.keys()) == {
        "task_instruction",
        "candidate_id",
        "conversation_id",
        "before_node_id",
        "after_node_id",
        "before_context",
        "after_context",
        "m4_2a_evidence",
    }
    assert "before_work_unit" not in payload
    assert "after_work_unit" not in payload


def test_v0_3_no_gold_pilot_ids_or_examples():
    # Invariant J: no Gold IDs and no few-shot examples in the instruction.
    upper = TASK_INSTRUCTION.upper()
    assert "GOLD-" not in upper
    assert "GOLD PILOT" not in upper
    assert "EXAMPLE:" not in upper
    assert "FOR EXAMPLE" not in upper
