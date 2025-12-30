"""Materialize generated testcases into relational entities and ES docs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .converters import (
    normalize_relations,
    normalize_scene_mappings,
    to_case_scene,
    to_test_case,
    to_test_case_index_document,
)
from .db_models import (
    CaseRelation,
    CaseScene,
    CaseSceneMapping,
    TestCase,
    TestCaseIndexDocument,
)


@dataclass
class MaterializedBundle:
    """Container of entities ready for persistence."""

    test_cases: List[TestCase]
    scenes: List[CaseScene]
    scene_mappings: List[CaseSceneMapping]
    relations: List[CaseRelation]
    index_docs: List[TestCaseIndexDocument]


def materialize_generation_outputs(
    generated: Dict[str, Any],
    *,
    output_dir: str = "outputs/testcases",
    default_env: str = "台架",
    default_source: str = "需求",
    default_owner: str | None = None,
    default_executor: str | None = "agent",
) -> MaterializedBundle:
    """Convert generator outputs to entity bundle and write text artifacts.

    Steps content and expected results are saved to disk to satisfy the
    relational schema (path-based storage) while full text is preserved for
    ES indexing.
    """

    base_dir = Path(output_dir)
    steps_dir = base_dir / "steps"
    expected_dir = base_dir / "expected"
    scenes_dir = base_dir / "scenes"
    for folder in (steps_dir, expected_dir, scenes_dir):
        folder.mkdir(parents=True, exist_ok=True)

    scenes_raw: List[Dict[str, Any]] = generated.get("scenes", []) or []
    mappings_raw: List[Dict[str, Any]] = generated.get("scene_mappings", []) or []
    relations_raw: List[Dict[str, Any]] = generated.get("relations", []) or []

    # Persist scene descriptions (if any) to files and build entities.
    scene_lookup: Dict[str, Dict[str, Any]] = {}
    scenes: List[CaseScene] = []
    for raw_scene in scenes_raw:
        scene_id = raw_scene["scene_id"]
        desc_content = raw_scene.get("scene_desc")
        if desc_content:
            desc_path = scenes_dir / f"{scene_id}.md"
            _write_text(desc_path, desc_content)
            raw_scene = {**raw_scene, "scene_desc_path": desc_path.as_posix()}
        scenes.append(to_case_scene(raw_scene))
        scene_lookup[scene_id] = raw_scene

    scene_mappings: List[CaseSceneMapping] = normalize_scene_mappings(mappings_raw)
    relations: List[CaseRelation] = normalize_relations(relations_raw)

    # Build per-case scene lists for ES docs.
    case_to_scene_ids: Dict[str, List[str]] = {}
    for mapping in scene_mappings:
        case_to_scene_ids.setdefault(mapping.case_id, []).append(mapping.scene_id)

    test_cases: List[TestCase] = []
    index_docs: List[TestCaseIndexDocument] = []

    for raw_case in generated.get("testcases", []) or []:
        case_id = raw_case["case_id"]
        steps_field = raw_case.get("steps", [])
        if isinstance(steps_field, list):
            steps_content = "\n".join(str(step) for step in steps_field)
        else:
            steps_content = str(steps_field)

        expected_result_content = str(raw_case.get("expected_result", ""))

        steps_path = steps_dir / f"{case_id}_steps.txt"
        expected_path = expected_dir / f"{case_id}_expected.txt"
        _write_text(steps_path, steps_content)
        _write_text(expected_path, expected_result_content)

        test_case = to_test_case(
            raw_case,
            steps_path=steps_path.as_posix(),
            expected_result_path=expected_path.as_posix(),
            default_env=default_env,
            default_source=default_source,
            default_owner=default_owner,
            default_executor=default_executor,
        )
        test_cases.append(test_case)

        scene_ids = case_to_scene_ids.get(case_id, [])
        scene_names = [scene_lookup.get(scene_id, {}).get("scene_name", scene_id) for scene_id in scene_ids]

        metadata = raw_case.get("_metadata", {}) if isinstance(raw_case, dict) else {}
        module_id = metadata.get("module_id") or raw_case.get("module")
        module_name = raw_case.get("module")

        index_docs.append(
            to_test_case_index_document(
                test_case,
                steps_content=steps_content,
                expected_result_content=expected_result_content,
                scene_ids=scene_ids,
                scene_names=scene_names,
                module_id=module_id,
                module_name=module_name,
            )
        )

    return MaterializedBundle(
        test_cases=test_cases,
        scenes=scenes,
        scene_mappings=scene_mappings,
        relations=relations,
        index_docs=index_docs,
    )


def _write_text(path: Path, content: str) -> None:
    """Persist text content to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
