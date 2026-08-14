"""Load EnterpriseRAG-Bench questions and documents into typed dataclasses.

Expects the dataset to be manually downloaded and extracted:
    data_dir/
        questions.jsonl
        extra_questions.jsonl        (optional)
        documents/                   (extracted from all_documents.zip)
            .../*.json
"""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.schema import BenchDocument, BenchQuestion


def load_questions(data_dir: Path, *, include_extra: bool = True) -> list[BenchQuestion]:
    """Load all questions from JSONL files."""
    files = ["questions.jsonl"]
    if include_extra:
        files.append("extra_questions.jsonl")

    questions: list[BenchQuestion] = []
    for fname in files:
        qf = data_dir / fname
        if not qf.exists():
            continue
        for line in qf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            questions.append(
                BenchQuestion(
                    question_id=raw["question_id"],
                    question=raw["question"],
                    question_type=raw.get("question_type", ""),
                    expected_doc_ids=raw.get("expected_doc_ids", []),
                    gold_answer=raw.get("gold_answer", ""),
                    answer_facts=raw.get("answer_facts", []),
                    metadata={"source_types": raw.get("source_types", [])},
                )
            )
    return questions


def _build_uuid_index(docs_root: Path) -> dict[str, Path]:
    """Scan all JSON files and map dataset_doc_uuid → file path."""
    index: dict[str, Path] = {}
    for jf in docs_root.rglob("*.json"):
        try:
            raw = json.loads(jf.read_text(encoding="utf-8"))
            uid = raw.get("dataset_doc_uuid", "")
            if uid:
                index[uid] = jf
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return index


def _parse_doc(path: Path, raw: dict) -> BenchDocument:
    """Parse a single JSON document into a BenchDocument."""
    title_field = raw.get("title_field_name", "title")
    content_field_names = raw.get("content_field_names", [])
    title = str(raw.get(title_field, "(untitled)"))

    content_fields: dict[str, str] = {}
    for field_name in content_field_names:
        val = raw.get(field_name)
        if val is None:
            continue
        if isinstance(val, str):
            content_fields[field_name] = val
        elif isinstance(val, list):
            parts = []
            for item in val:
                parts.append(
                    json.dumps(item, indent=2, ensure_ascii=False)
                    if isinstance(item, dict)
                    else str(item)
                )
            content_fields[field_name] = "\n\n".join(parts)
        else:
            content_fields[field_name] = json.dumps(val, indent=2, ensure_ascii=False)

    skip_keys = {title_field, "title_field_name", "content_field_names", "dataset_doc_uuid"}
    skip_keys.update(content_field_names)
    metadata = {k: v for k, v in raw.items() if k not in skip_keys}

    return BenchDocument(
        doc_id=raw.get("dataset_doc_uuid", ""),
        title=title,
        source_path=path,
        content_fields=content_fields,
        metadata=metadata,
    )


def load_documents(
    data_dir: Path, needed_uuids: set[str]
) -> dict[str, BenchDocument]:
    """Load only the documents referenced by the given UUIDs.

    Returns {uuid: BenchDocument}.
    """
    docs_root = data_dir / "documents"
    if not docs_root.exists():
        raise FileNotFoundError(f"Documents directory not found: {docs_root}")

    uuid_index = _build_uuid_index(docs_root)
    docs: dict[str, BenchDocument] = {}
    for uid in needed_uuids:
        path = uuid_index.get(uid)
        if path is None:
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        docs[uid] = _parse_doc(path, raw)

    missing = needed_uuids - set(docs)
    if missing:
        print(f"  warning: {len(missing)} doc UUIDs not found in documents/")

    return docs
