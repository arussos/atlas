"""
M4.2a — Tests for tools/episodes/text.py

Covers spec section 17.E: text, multimodal_text, mixed parts, unknown
type, empty parts, thoughts/reasoning_recap exclusion.
"""

from tools.episodes.text import extract_visible_text


def test_text_content_type_extracted():
    content = {"content_type": "text", "parts": ["hello world"]}
    assert extract_visible_text("text", content) == "hello world"


def test_text_content_type_multiple_parts_joined_stably():
    content = {"content_type": "text", "parts": ["first", "second"]}
    assert extract_visible_text("text", content) == "first\nsecond"


def test_multimodal_text_string_parts_extracted():
    content = {"content_type": "multimodal_text", "parts": ["check this image"]}
    assert extract_visible_text("multimodal_text", content) == "check this image"


def test_multimodal_text_mixed_parts_ignores_non_string_items():
    content = {
        "content_type": "multimodal_text",
        "parts": [
            {"content_type": "image_asset_pointer", "asset_pointer": "file-service://file-x"},
            "check this image",
        ],
    }
    assert extract_visible_text("multimodal_text", content) == "check this image"


def test_unknown_content_type_returns_empty_string():
    content = {"content_type": "code", "text": "print(1)"}
    assert extract_visible_text("code", content) == ""


def test_unknown_content_type_does_not_crash():
    assert extract_visible_text("some_new_future_type", {"anything": "goes"}) == ""
    assert extract_visible_text("some_new_future_type", None) == ""
    assert extract_visible_text("some_new_future_type", "not-a-dict") == ""


def test_empty_parts_returns_empty_string():
    content = {"content_type": "text", "parts": []}
    assert extract_visible_text("text", content) == ""


def test_missing_parts_returns_empty_string():
    content = {"content_type": "text"}
    assert extract_visible_text("text", content) == ""


def test_malformed_content_does_not_crash():
    assert extract_visible_text("text", None) == ""
    assert extract_visible_text("text", "not-a-dict") == ""
    assert extract_visible_text("text", 42) == ""


def test_thoughts_excluded_even_if_parts_present():
    content = {"content_type": "thoughts", "parts": ["internal reasoning here"]}
    assert extract_visible_text("thoughts", content) == ""


def test_reasoning_recap_excluded_even_if_parts_present():
    content = {"content_type": "reasoning_recap", "parts": ["recap of reasoning"]}
    assert extract_visible_text("reasoning_recap", content) == ""


def test_none_content_type_returns_empty_string():
    assert extract_visible_text(None, {"parts": ["x"]}) == ""
