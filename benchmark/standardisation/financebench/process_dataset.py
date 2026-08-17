#!/usr/bin/env python3
"""Process the FinanceBench dataset into the shared benchmark schema.

Reads:
    benchmark/data/financebench/data/financebench_open_source.jsonl
    benchmark/data/financebench/data/financebench_document_information.jsonl
    benchmark/data/financebench/pdfs/*.pdf

Writes:
    benchmark/processed_data/financebench/questions.jsonl
    benchmark/processed_data/financebench/documents.jsonl
    benchmark/processed_data/financebench/doc_id_to_pdf.json   (doc_id → PDF path)

Usage:
    python -m benchmark.standardisation.financebench.process_dataset
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import typer

from benchmark.schema import BenchDocument, BenchQuestion

app = typer.Typer(add_completion=False)

PROCESSED_DIR = Path("benchmark/processed_data/financebench")


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------


def process_questions(data_dir: Path) -> list[BenchQuestion]:
    """Parse financebench_open_source.jsonl into BenchQuestion list."""
    qa_path = data_dir / "data" / "financebench_open_source.jsonl"
    questions: list[BenchQuestion] = []
    for line in qa_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        questions.append(
            BenchQuestion(
                question_id=raw["financebench_id"],
                question=raw["question"],
                question_type=raw.get("question_type", ""),
                expected_doc_ids=[raw["doc_name"]],
                gold_answer=raw["answer"],
                justification=raw.get("justification", ""),
                evidence=raw.get("evidence", []),
                metadata={
                    "company": raw.get("company", ""),
                    "question_reasoning": raw.get("question_reasoning", ""),
                    "dataset_subset_label": raw.get("dataset_subset_label", ""),
                    "domain_question_num": raw.get("domain_question_num"),
                },
            )
        )
    return questions


# ---------------------------------------------------------------------------
# Documents (metadata + PDF paths)
# ---------------------------------------------------------------------------


def _load_document_info(data_dir: Path) -> dict[str, dict]:
    """Load document metadata keyed by doc_name."""
    info_path = data_dir / "data" / "financebench_document_information.jsonl"
    docs: dict[str, dict] = {}
    for line in info_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            raw = json.loads(line)
            docs[raw["doc_name"]] = raw
    return docs


def process_documents(
    data_dir: Path, doc_info: dict[str, dict], needed_doc_names: set[str]
) -> list[BenchDocument]:
    """Build BenchDocument entries for referenced docs."""
    pdfs_dir = data_dir / "pdfs"
    documents: list[BenchDocument] = []
    for doc_name in sorted(needed_doc_names):
        pdf_path = pdfs_dir / f"{doc_name}.pdf"
        info = doc_info.get(doc_name, {})
        documents.append(
            BenchDocument(
                doc_id=doc_name,
                title=doc_name.replace("_", " "),
                source_path=pdf_path,
                metadata={
                    "company": info.get("company", ""),
                    "gics_sector": info.get("gics_sector", ""),
                    "doc_type": info.get("doc_type", ""),
                    "doc_period": info.get("doc_period"),
                    "doc_link": info.get("doc_link", ""),
                    "pdf_exists": pdf_path.exists(),
                },
            )
        )
    return documents


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def write_jsonl(items: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            data = asdict(item)
            if "source_path" in data:
                data["source_path"] = str(data["source_path"])
            f.write(json.dumps(data, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.command()
def main(
    data_dir: Path = typer.Option(
        Path("benchmark/data/financebench"), help="FinanceBench dataset root"
    ),
    output_dir: Path = typer.Option(PROCESSED_DIR, help="Output directory"),
):
    """Process FinanceBench dataset into the shared benchmark schema."""
    # 1. Questions
    print("processing questions ...")
    questions = process_questions(data_dir)
    print(f"  {len(questions)} questions")

    # 2. Document metadata
    print("loading document info ...")
    doc_info = _load_document_info(data_dir)
    needed = {doc_id for q in questions for doc_id in q.expected_doc_ids}
    documents = process_documents(data_dir, doc_info, needed)
    found = sum(1 for d in documents if d.metadata.get("pdf_exists"))
    print(f"  {found}/{len(documents)} PDFs found on disk")

    # 3. Write
    print(f"writing to {output_dir}/ ...")
    output_dir.mkdir(parents=True, exist_ok=True)

    write_jsonl(questions, output_dir / "questions.jsonl")
    write_jsonl(documents, output_dir / "documents.jsonl")

    pdf_map = {d.doc_id: str(d.source_path) for d in documents if d.source_path.exists()}
    (output_dir / "doc_id_to_pdf.json").write_text(
        json.dumps(pdf_map, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"done:")
    print(f"  {output_dir}/questions.jsonl      ({len(questions)} questions)")
    print(f"  {output_dir}/documents.jsonl      ({len(documents)} documents)")
    print(f"  {output_dir}/doc_id_to_pdf.json   ({len(pdf_map)} PDF paths)")


if __name__ == "__main__":
    app()
