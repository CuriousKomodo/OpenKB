#!/usr/bin/env python3
"""E2E benchmark: load processed dataset → ingest → query → results.

Usage:
    # Run FinanceBench (first 10 questions):
    python -m benchmark.run_bench run --dataset financebench --limit 10

    # Run EnterpriseRAG:
    python -m benchmark.run_bench run --dataset enterprise_rag --limit 10

    # Query only (KB already populated):
    python -m benchmark.run_bench run --dataset financebench --skip-ingest
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from benchmark.ingest import init_kb, ingest_all
from benchmark.schema import BenchQuestion
from benchmark.query import run_all


app = typer.Typer(add_completion=False)

OUTPUT_DIR = Path("benchmark/output")
PROCESSED_DIR = Path("benchmark/processed_data")
KB_ROOT = Path("benchmark/kbs")


def _resolve_model(kb_dir: Path) -> str:
    from openkb.config import resolve_effective_config

    return resolve_effective_config(kb_dir)[0].get("model", "gpt-4.1")


def _load_processed_questions(dataset_dir: Path) -> list[BenchQuestion]:
    """Load questions.jsonl from processed data into typed dataclasses."""
    qf = dataset_dir / "questions.jsonl"
    if not qf.exists():
        raise FileNotFoundError(f"{qf} not found — run the standardisation script first")
    questions: list[BenchQuestion] = []
    for line in qf.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        q = json.loads(line)
        questions.append(
            BenchQuestion(
                question_id=q["question_id"],
                question=q["question"],
                question_type=q.get("question_type", ""),
                expected_doc_ids=q.get("expected_doc_ids", []),
                gold_answer=q.get("gold_answer", ""),
                justification=q.get("justification", ""),
                answer_facts=q.get("answer_facts", []),
                evidence=q.get("evidence", []),
                metadata=q.get("metadata", {}),
            )
        )
    return questions


def _load_doc_paths(dataset_dir: Path) -> dict[str, Path]:
    """Load doc_id → file path mapping from processed data."""
    for name in ("doc_id_to_pdf.json", "doc_id_to_file.json"):
        p = dataset_dir / name
        if p.exists():
            return {k: Path(v) for k, v in json.loads(p.read_text(encoding="utf-8")).items()}
    return {}


@app.command()
def run(
    dataset: str = typer.Option(..., help="Dataset name (e.g. financebench, enterprise_rag)"),
    kb_root: Path = typer.Option(KB_ROOT, help="Root for benchmark KBs"),
    limit: int = typer.Option(0, help="Max questions (0=all)"),
    skip_ingest: bool = typer.Option(False, help="Skip ingestion"),
    ingest_all_docs: bool = typer.Option(False, "--ingest-all", help="Ingest all docs, not just question-referenced"),
):
    """Run the full E2E benchmark pipeline for a dataset."""
    dataset_dir = PROCESSED_DIR / dataset
    questions = _load_processed_questions(dataset_dir)
    if limit > 0:
        questions = questions[:limit]
    print(f"loaded {len(questions)} questions from {dataset}")

    kb_dir = init_kb(kb_root, dataset)
    resolved_model = _resolve_model(kb_dir)
    results_path = OUTPUT_DIR / dataset / "results.jsonl"

    if not skip_ingest:
        all_paths = _load_doc_paths(dataset_dir)
        if ingest_all_docs:
            doc_id_to_path = all_paths
        else:
            needed = {d for q in questions for d in q.expected_doc_ids if d}
            doc_id_to_path = {doc_id: all_paths[doc_id] for doc_id in needed if doc_id in all_paths}
            missing = needed - set(doc_id_to_path)
            if missing:
                print(f"  warning: {len(missing)} docs not in path mapping")

        print(f"ingesting {len(doc_id_to_path)} documents ...")
        outcomes = ingest_all(doc_id_to_path, kb_dir, resolved_model)
        added = sum(1 for v in outcomes.values() if v == "added")
        failed = sum(1 for v in outcomes.values() if v == "failed")
        print(f"  ingestion done: {added} added, {failed} failed")

    # print("running queries ...")
    # results = run_all(questions, kb_dir, resolved_model, results_path)
    # print(f"done. {len(results)} new results → {results_path}")


if __name__ == "__main__":
    app()
