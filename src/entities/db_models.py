"""Data entities aligned with relational tables and ES index."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator


DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


class CaseLevel(str, Enum):
    """Allowed test case levels."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class CaseStatus(str, Enum):
    """Allowed execution statuses."""

    OK = "OK"
    NOK = "NOK"
    BLOCK = "BLOCK"
    NA = "NA"



class RelationType(str, Enum):
    """Relationship types between cases."""

    DEPENDS_ON = "dependency"
    RELATED_TO = "association"
    BLOCKS = "block"
    DERIVED_FROM = "derivative"


class TestCase(BaseModel):
    """Relational test_case row."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore", populate_by_name=True)

    case_id: str
    project_name: Optional[str] = None
    module: str
    feature: str
    title: str
    precondition: Optional[str] = None
    steps_path: str
    expected_result_path: str
    level: CaseLevel
    source: Optional[str] = None
    environment: Optional[str] = None
    owner: Optional[str] = None
    status: CaseStatus = CaseStatus.NA
    remark: Optional[str] = None
    create_time: datetime
    update_time: datetime
    executor: Optional[str] = None

    @field_validator("create_time", "update_time", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.strptime(value, DATETIME_FMT)
        raise ValueError("Datetime must be str or datetime instance")

    @field_serializer("create_time", "update_time")
    def _serialize_datetime(self, value: datetime) -> str:
        return value.strftime(DATETIME_FMT)


class CaseRelation(BaseModel):
    """Relational case_relation row."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore", populate_by_name=True)

    relation_id: str
    source_case_id: str
    target_case_id: str
    relation_type: RelationType
    remark: Optional[str] = None
    create_time: datetime

    @field_validator("create_time", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.strptime(value, DATETIME_FMT)
        raise ValueError("Datetime must be str or datetime instance")

    @field_serializer("create_time")
    def _serialize_datetime(self, value: datetime) -> str:
        return value.strftime(DATETIME_FMT)


class CaseScene(BaseModel):
    """Relational case_scene row."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore", populate_by_name=True)

    scene_id: str
    scene_name: str
    scene_desc_path: Optional[str] = None
    create_time: datetime

    @field_validator("create_time", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.strptime(value, DATETIME_FMT)
        raise ValueError("Datetime must be str or datetime instance")

    @field_serializer("create_time")
    def _serialize_datetime(self, value: datetime) -> str:
        return value.strftime(DATETIME_FMT)


class CaseSceneMapping(BaseModel):
    """Relational case_scene_mapping row."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore", populate_by_name=True)

    mapping_id: str
    scene_id: str
    case_id: str
    create_time: datetime

    @field_validator("create_time", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.strptime(value, DATETIME_FMT)
        raise ValueError("Datetime must be str or datetime instance")

    @field_serializer("create_time")
    def _serialize_datetime(self, value: datetime) -> str:
        return value.strftime(DATETIME_FMT)


class TestCaseIndexDocument(BaseModel):
    """Elasticsearch document for test_case_index."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore", populate_by_name=True)

    case_id: str
    title: str
    module_id: str
    module_name: str
    status: CaseStatus
    steps: str
    expected_result: str
    executor: Optional[str] = None
    create_time: datetime
    scene_ids: List[str] = Field(default_factory=list)
    scene_names: List[str] = Field(default_factory=list)

    @field_validator("create_time", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.strptime(value, DATETIME_FMT)
        raise ValueError("Datetime must be str or datetime instance")

    @field_serializer("create_time")
    def _serialize_datetime(self, value: datetime) -> str:
        return value.strftime(DATETIME_FMT)
