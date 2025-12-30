"""Helpers to convert raw generator outputs into entity models."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Sequence

from .db_models import (
    DATETIME_FMT,
    CasePriority,
    CaseRelation,
    CaseScene,
    CaseSceneMapping,
    CaseStatus,
    RelationType,
    TestCase,
    TestCaseIndexDocument,
)


def _coerce_datetime(value: Optional[object]) -> datetime:
    """Normalize datetime-like input using the project-wide format."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.strptime(value, DATETIME_FMT)
    return datetime.now()


def to_test_case(
    raw_case: dict,
    *,
    steps_path: str,
    expected_result_path: str,
    default_env: str = "台架",
    default_source: str = "需求",
    default_owner: Optional[str] = None,
    default_executor: Optional[str] = "agent",
) -> TestCase:
    """Build a TestCase entity from generator output and storage paths."""
    now = _coerce_datetime(raw_case.get("create_time"))
    return TestCase(
        case_id=raw_case["case_id"],
        project_name=raw_case.get("project_name"),
        module=raw_case["module"],
        feature=raw_case["feature"],
        title=raw_case["title"],
        precondition=raw_case.get("precondition"),
        steps_path=steps_path,
        expected_result_path=expected_result_path,
        level=raw_case["level"],
        source=raw_case.get("source", default_source),
        environment=raw_case.get("environment", default_env),
        owner=raw_case.get("owner", default_owner),
        status=raw_case.get("status", CaseStatus.NA),
        remark=raw_case.get("remark"),
        priority=raw_case.get("priority"),
        create_time=now,
        update_time=_coerce_datetime(raw_case.get("update_time") or now),
        executor=raw_case.get("executor", default_executor),
    )


def to_case_scene(raw_scene: dict) -> CaseScene:
    """Build a CaseScene entity from generator output."""
    return CaseScene(
        scene_id=raw_scene["scene_id"],
        scene_name=raw_scene.get("scene_name", raw_scene["scene_id"]),
        scene_desc_path=raw_scene.get("scene_desc_path") or raw_scene.get("scene_desc"),
        create_time=_coerce_datetime(raw_scene.get("create_time")),
    )


def to_case_scene_mapping(raw_mapping: dict) -> CaseSceneMapping:
    """Build a CaseSceneMapping entity from generator output."""
    return CaseSceneMapping(
        mapping_id=raw_mapping["mapping_id"],
        scene_id=raw_mapping["scene_id"],
        case_id=raw_mapping["case_id"],
        create_time=_coerce_datetime(raw_mapping.get("create_time")),
    )


def to_case_relation(raw_relation: dict) -> CaseRelation:
    """Build a CaseRelation entity from generator output."""
    return CaseRelation(
        relation_id=raw_relation["relation_id"],
        source_case_id=raw_relation["source_case_id"],
        target_case_id=raw_relation["target_case_id"],
        relation_type=raw_relation.get("relation_type", RelationType.RELATED_TO),
        remark=raw_relation.get("remark"),
        create_time=_coerce_datetime(raw_relation.get("create_time")),
    )


def to_test_case_index_document(
    case: TestCase,
    *,
    steps_content: str,
    expected_result_content: str,
    scene_ids: Sequence[str] = (),
    scene_names: Sequence[str] = (),
    module_id: Optional[str] = None,
    module_name: Optional[str] = None,
) -> TestCaseIndexDocument:
    """Build ES document aligned with test_case_index mapping."""
    return TestCaseIndexDocument(
        case_id=case.case_id,
        title=case.title,
        module_id=module_id or case.module,
        module_name=module_name or case.module,
        priority=case.priority or CasePriority.MEDIUM,
        status=case.status,
        steps=steps_content,
        expected_result=expected_result_content,
        executor=case.executor,
        create_time=case.create_time,
        scene_ids=list(scene_ids),
        scene_names=list(scene_names),
    )


def normalize_scene_mappings(
    mappings: Iterable[dict],
) -> list[CaseSceneMapping]:
    """Convert an iterable of raw mapping dicts into CaseSceneMapping entities."""
    return [to_case_scene_mapping(mapping) for mapping in mappings]


def normalize_relations(relations: Iterable[dict]) -> list[CaseRelation]:
    """Convert an iterable of raw relation dicts into CaseRelation entities."""
    return [to_case_relation(item) for item in relations]
