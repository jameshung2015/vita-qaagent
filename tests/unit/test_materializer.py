import json
from pathlib import Path

from src.entities import DATETIME_FMT, materialize_generation_outputs


def test_materialize_generation_outputs_creates_files_and_entities(tmp_path):
    now_str = "2025-01-02 03:04:05"

    generated = {
        "testcases": [
            {
                "case_id": "case_1",
                "module": "module_a",
                "feature": "feature_x",
                "title": "Login happy",
                "precondition": "pre",
                "steps": ["open page", "input user"],
                "expected_result": "login success",
                "level": "P1",
                "status": "OK",
                "create_time": now_str,
                "update_time": now_str,
                "_metadata": {"module_id": "module_a"},
            }
        ],
        "scenes": [
            {
                "scene_id": "scene_1",
                "scene_name": "Happy path",
                "scene_desc": "desc text",
                "create_time": now_str,
            }
        ],
        "scene_mappings": [
            {
                "mapping_id": "map_1",
                "scene_id": "scene_1",
                "case_id": "case_1",
                "create_time": now_str,
            }
        ],
        "relations": [],
    }

    bundle = materialize_generation_outputs(generated, output_dir=str(tmp_path))

    # Files are created
    steps_file = Path(tmp_path) / "steps" / "case_1_steps.txt"
    expected_file = Path(tmp_path) / "expected" / "case_1_expected.txt"
    scene_desc_file = Path(tmp_path) / "scenes" / "scene_1.md"

    assert steps_file.exists(), "steps file should be created"
    assert expected_file.exists(), "expected result file should be created"
    assert scene_desc_file.exists(), "scene desc file should be created"

    assert steps_file.read_text(encoding="utf-8").strip() == "open page\ninput user"
    assert expected_file.read_text(encoding="utf-8").strip() == "login success"
    assert scene_desc_file.read_text(encoding="utf-8").strip() == "desc text"

    # Entities are populated
    assert len(bundle.test_cases) == 1
    assert len(bundle.index_docs) == 1
    assert len(bundle.scenes) == 1
    assert len(bundle.scene_mappings) == 1

    test_case = bundle.test_cases[0]
    assert test_case.case_id == "case_1"
    assert test_case.module == "module_a"
    assert test_case.feature == "feature_x"
    assert test_case.priority.value == "high"  # derived from level P1

    # Datetime serialization
    dumped_case = test_case.model_dump()
    assert dumped_case["create_time"] == now_str
    assert dumped_case["update_time"] == now_str

    # ES document content
    doc = bundle.index_docs[0]
    dumped_doc = doc.model_dump()
    assert dumped_doc["case_id"] == "case_1"
    assert dumped_doc["steps"] == "open page\ninput user"
    assert dumped_doc["expected_result"] == "login success"
    assert dumped_doc["scene_ids"] == ["scene_1"]
    assert dumped_doc["scene_names"] == ["Happy path"]
    assert dumped_doc["create_time"] == now_str

    # Scene path stored on entity
    scene_entity = bundle.scenes[0]
    assert scene_entity.scene_desc_path.endswith("scene_1.md")
    assert Path(scene_entity.scene_desc_path).exists()
