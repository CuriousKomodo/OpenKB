#!/usr/bin/env python3
"""E2E benchmark: load dataset → prepare docs → ingest → query → results.

Usage:
    # Run full pipeline (first 10 questions):
    python -m benchmark.run_bench run --data-dir benchmark/data --limit 10

    # Run queries only (KB already populated):
    python -m benchmark.run_bench run --data-dir benchmark/data --skip-ingest

    # Just prepare markdown files (no ingestion or queries):
    python -m benchmark.run_bench prepare --data-dir benchmark/data
"""

from __future__ import annotations

from pathlib import Path

import typer

from benchmark.load_dataset import load_documents, load_questions
from benchmark.prepare_docs import prepare_all

app = typer.Typer(add_completion=False)

OUTPUT_DIR = Path("benchmark/output")


def _resolve_model(kb_dir: Path, model: str | None) -> str:
    if model:
        return model
    try:
        from openkb.config import resolve_effective_config

        return resolve_effective_config(kb_dir)[0].get("model", "gpt-4.1")
    except Exception:
        return "gpt-4.1"


@app.command()
def prepare(
    data_dir: Path = typer.Option(Path("benchmark/data"), help="Dataset root"),
):
    """Convert dataset JSON docs to markdown (no ingestion)."""
    questions = load_questions(data_dir)
    print(f"loaded {len(questions)} questions")

    needed = {uid for q in questions for uid in q.expected_doc_ids if uid}
    print(f"loading {len(needed)} referenced documents ...")
    docs = load_documents(data_dir, needed)

    md_dir = data_dir / "md"
    uuid_to_md = prepare_all(docs, md_dir)
    print(f"prepared {len(uuid_to_md)} markdown files in {md_dir}")


@app.command()
def run(
    data_dir: Path = typer.Option(Path("benchmark/data"), help="Dataset root"),
    kb_dir: Path = typer.Option(Path("/tmp/openkb-bench"), help="KB directory"),
    limit: int = typer.Option(0, help="Max questions (0=all)"),
    model: str = typer.Option(None, help="LLM model override"),
    skip_ingest: bool = typer.Option(False, help="Skip ingestion"),
    include_extra: bool = typer.Option(True, help="Include extra_questions.jsonl"),
):
    """Run the full E2E benchmark pipeline."""
    # 1. Load
    questions = load_questions(data_dir, include_extra=include_extra)
    if limit > 0:
        questions = questions[:limit]
    print(f"loaded {len(questions)} questions")

    resolved_model = _resolve_model(kb_dir, model)
    results_path = OUTPUT_DIR / "results.jsonl"

    if not skip_ingest:
        # 2. Prepare
        needed = {uid for q in questions for uid in q.expected_doc_ids if uid}
        print(f"loading {len(needed)} referenced documents ...")
        docs = load_documents(data_dir, needed)

        md_dir = data_dir / "md"
        print("preparing markdown files ...")
        uuid_to_md = prepare_all(docs, md_dir)
        print(f"  {len(uuid_to_md)} docs ready")

        # 3. Ingest
        from benchmark.ingest import ingest_all

        print("ingesting documents ...")
        outcomes = ingest_all(uuid_to_md, kb_dir)
        added = sum(1 for v in outcomes.values() if v == "added")
        failed = sum(1 for v in outcomes.values() if v == "failed")
        print(f"  ingestion done: {added} added, {failed} failed")

    # 4. Query
    from benchmark.query import run_all

    print("running queries ...")
    results = run_all(questions, kb_dir, resolved_model, results_path)
    print(f"done. {len(results)} new results → {results_path}")


if __name__ == "__main__":
    app()
