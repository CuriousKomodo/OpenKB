"""Data classes for EnterpriseRAG-Bench items."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BenchDocument:
    """A single enterprise document from the dataset."""

    uuid: str
    title: str
    source_path: Path  # original JSON path in the dataset
    content_fields: dict[str, str]  # field_name → rendered text
    metadata: dict  # everything else

    @property
    def slug(self) -> str:
        return self.uuid


@dataclass
class BenchQuestion:
    """A single benchmark question with ground-truth."""

    question_id: str
    question: str
    question_type: str
    source_types: list[str]
    expected_doc_ids: list[str]
    gold_answer: str
    answer_facts: list[str]


@dataclass
class BenchResult:
    """Result of running one question through the pipeline."""

    question_id: str
    question: str
    question_type: str
    source_types: list[str]
    expected_doc_ids: list[str]
    predicted: str
    gold_answer: str
    answer_facts: list[str]
    error: str | None = None
