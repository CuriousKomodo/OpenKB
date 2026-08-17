#!/usr/bin/env python3
"""Process the EnterpriseRAG-Bench dataset into the shared benchmark schema.

Only the Confluence subset of documents is available (as .txt files).
Questions referencing docs not on disk are kept but flagged in metadata.

Reads:
    benchmark/data/enterprise_rag/questions.jsonl
    benchmark/data/enterprise_rag/confluence/*.txt

Writes:
    benchmark/processed_data/enterprise_rag/questions.jsonl
    benchmark/processed_data/enterprise_rag/documents.jsonl
    benchmark/processed_data/enterprise_rag/doc_id_to_file.json

Usage:
    python -m benchmark.standardisation.enterprise_rag.process_dataset
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import typer

from benchmark.schema import BenchDocument, BenchQuestion

app = typer.Typer(add_completion=False)

PROCESSED_DIR = Path("benchmark/processed_data/enterprise_rag")


def _build_doc_index(confluence_dir: Path) -> dict[str, Path]:
    """Map dsid_* → file path from confluence .txt filenames."""
    index: dict[str, Path] = {}
    for f in confluence_dir.iterdir():
        if not f.is_file():
            continue
        # Filenames: dsid_<hex>__<slug>.txt
        doc_id = f.name.split("__")[0]
        if doc_id:
            index[doc_id] = f
    return index


def _title_from_filename(filename: str) -> str:
    """Extract a readable title from the confluence filename."""
    # dsid_<hex>__<slug>.txt → slug → replace hyphens with spaces → title case
    parts = filename.split("__", 1)
    if len(parts) < 2:
        return filename
    slug = parts[1].rsplit(".", 1)[0]
    return slug.replace("-", " ").replace("_", " ").strip().title()


def process_questions(data_dir: Path) -> list[BenchQuestion]:
    """Parse questions.jsonl into BenchQuestion list."""
    qa_path = data_dir / "questions.jsonl"
    questions: list[BenchQuestion] = []
    for line in qa_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
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
                metadata={
                    "source_types": raw.get("source_types", []),
                },
            )
        )
    return questions


def process_documents(
    data_dir: Path, needed_doc_ids: set[str]
) -> list[BenchDocument]:
    """Build BenchDocument entries for referenced docs found in confluence/."""
    confluence_dir = data_dir / "confluence"
    doc_index = _build_doc_index(confluence_dir)

    documents: list[BenchDocument] = []
    for doc_id in sorted(needed_doc_ids):
        path = doc_index.get(doc_id)
        if path is None:
            continue
        documents.append(
            BenchDocument(
                doc_id=doc_id,
                title=_title_from_filename(path.name),
                source_path=path,
                metadata={"source_type": "confluence"},
            )
        )
    return documents


def write_jsonl(items: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            data = asdict(item)
            if "source_path" in data:
                data["source_path"] = str(data["source_path"])
            f.write(json.dumps(data, ensure_ascii=False) + "\n")


@app.command()
def main(
    data_dir: Path = typer.Option(
        Path("benchmark/data/enterprise_rag"), help="EnterpriseRAG dataset root"
    ),
    output_dir: Path = typer.Option(PROCESSED_DIR, help="Output directory"),
):
    """Process EnterpriseRAG-Bench dataset into the shared benchmark schema."""
    # 1. Questions
    print("processing questions ...")
    questions = process_questions(data_dir)
    print(f"  {len(questions)} questions")

    # 2. Documents (confluence subset only)
    needed = {doc_id for q in questions for doc_id in q.expected_doc_ids}
    print(f"processing documents ({len(needed)} referenced) ...")
    documents = process_documents(data_dir, needed)
    available_ids = {d.doc_id for d in documents}
    print(f"  {len(documents)}/{len(needed)} docs found in confluence/")

    # Tag questions by doc availability
    answerable = sum(
        1 for q in questions
        if all(d in available_ids for d in q.expected_doc_ids) and q.expected_doc_ids
    )
    print(f"  {answerable} questions have all referenced docs available")

    # 3. Write
    print(f"writing to {output_dir}/ ...")
    write_jsonl(questions, output_dir / "questions.jsonl")
    write_jsonl(documents, output_dir / "documents.jsonl")

    doc_file_map = {d.doc_id: str(d.source_path) for d in documents}
    (output_dir / "doc_id_to_file.json").write_text(
        json.dumps(doc_file_map, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"done:")
    print(f"  {output_dir}/questions.jsonl    ({len(questions)} questions)")
    print(f"  {output_dir}/documents.jsonl    ({len(documents)} documents)")
    print(f"  {output_dir}/doc_id_to_file.json ({len(doc_file_map)} file mappings)")


if __name__ == "__main__":
    app()
