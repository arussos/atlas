"""
M4.1 — Shared synthetic fixture builders for the ChatGPT normalizer tests.

All data here is synthetic and contains no real conversation content, per
the M4.1 raw-data policy.
"""

import json
import zipfile


def _msg(msg_id: str, role: str, text: str, create_time: float, extra_content: dict = None) -> dict:
    content = {"content_type": "text", "parts": [text]}
    if extra_content:
        content.update(extra_content)
    return {
        "id": msg_id,
        "author": {"role": role},
        "create_time": create_time,
        "content": content,
    }


def branching_fixture(current_node: str = "c_user") -> dict:
    """
    Builds the fixture described in the M4.1 spec:

        root
         |
        user A
         |
        assistant A
         |
        user B
        / \\
     asst B1  asst B2
                |
              user C

    current_node defaults to the B2 -> C branch.
    """
    mapping = {
        "root": {"id": "root", "parent": None, "message": None},
        "a_user": {"id": "a_user", "parent": "root", "message": _msg("m-a-user", "user", "hi", 1.0)},
        "a_asst": {"id": "a_asst", "parent": "a_user", "message": _msg("m-a-asst", "assistant", "hello", 2.0)},
        "b_user": {"id": "b_user", "parent": "a_asst", "message": _msg("m-b-user", "user", "question", 3.0)},
        "b1_asst": {"id": "b1_asst", "parent": "b_user", "message": _msg("m-b1", "assistant", "answer 1", 4.0)},
        "b2_asst": {"id": "b2_asst", "parent": "b_user", "message": _msg("m-b2", "assistant", "answer 2", 4.5)},
        "c_user": {"id": "c_user", "parent": "b2_asst", "message": _msg("m-c", "user", "follow up", 5.0)},
    }
    return {
        "id": "conv-branch",
        "title": "Branch test",
        "create_time": 1.0,
        "update_time": 5.0,
        "current_node": current_node,
        "default_model_slug": "gpt-test",
        "is_archived": False,
        "mapping": mapping,
    }


def multimodal_fixture() -> dict:
    mapping = {
        "root": {"id": "root", "parent": None, "message": None},
        "user_1": {
            "id": "user_1",
            "parent": "root",
            "message": {
                "id": "m-user-1",
                "author": {"role": "user"},
                "create_time": 1.0,
                "content": {
                    "content_type": "multimodal_text",
                    "parts": [
                        {
                            "content_type": "image_asset_pointer",
                            "asset_pointer": "file-service://file-2DDLLAw1iPRMn5T7MiTVqFLC",
                            "width": 100,
                            "height": 100,
                        },
                        "check this image",
                    ],
                },
            },
        },
    }
    return {
        "id": "conv-multimodal",
        "title": "Multimodal test",
        "create_time": 1.0,
        "update_time": 1.0,
        "current_node": "user_1",
        "mapping": mapping,
    }


def write_synthetic_export(zip_path) -> None:
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "export_manifest.json",
            json.dumps({"export_files": ["conversations-000.json"]}),
        )
        zf.writestr("conversations-000.json", json.dumps([branching_fixture(), multimodal_fixture()]))
        zf.writestr(
            "conversation_asset_file_names.json",
            json.dumps({"file-2DDLLAw1iPRMn5T7MiTVqFLC.dat": "image.png"}),
        )
        zf.writestr("file-2DDLLAw1iPRMn5T7MiTVqFLC.dat", b"fake-image-bytes")
