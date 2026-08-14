"""Shared data classes for benchmark datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BenchDocument:
    """A document referenced by benchmark questions."""

    doc_id: str  # unique identifier (uuid for EnterpriseRAG, doc_name for FinanceBench)
    title: str
    source_path: Path  # path to the original file (JSON, PDF, etc.)
    content_fields: dict[str, str] = field(default_factory=dict)  # field_name → text
    metadata: dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        return self.doc_id


@dataclass
class BenchQuestion:
    """A benchmark question with ground-truth answer."""

    question_id: str
    question: str
    question_type: str
    expected_doc_ids: list[str]  # doc_ids this question is about
    gold_answer: str
    justification: str = ""  # human explanation of the answer
    answer_facts: list[str] = field(default_factory=list)  # atomic facts (EnterpriseRAG)
    evidence: list[dict] = field(default_factory=list)  # evidence passages (FinanceBench)
    metadata: dict = field(default_factory=dict)  # dataset-specific fields


@dataclass
class BenchResult:
    """Result of running one question through the pipeline."""

    question_id: str
    question: str
    question_type: str
    expected_doc_ids: list[str]
    predicted: str
    gold_answer: str
    justification: str = ""
    answer_facts: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    error: str | None = None
