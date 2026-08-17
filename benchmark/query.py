"""Run benchmark questions against an OpenKB knowledge base."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from openkb.agent.query import run_query

from benchmark.schema import BenchQuestion, BenchResult


def _load_answered(results_path: Path) -> set[str]:
    """Load question_ids already in results.jsonl."""
    done: set[str] = set()
    if not results_path.exists():
        return done
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                done.add(json.loads(line)["question_id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return done


async def _query_one(question: str, kb_dir: Path, model: str) -> str:
    return await run_query(question, kb_dir, model, stream=False)


def run_all(
    questions: list[BenchQuestion],
    kb_dir: Path,
    model: str,
    results_path: Path,
) -> list[BenchResult]:
    """Run each question, append results to JSONL, return all results.

    Resume-safe: skips question_ids already in results_path.
    """
    done = _load_answered(results_path)
    pending = [q for q in questions if q.question_id not in done]
    print(f"  {len(done)} already answered, {len(pending)} remaining")

    results_path.parent.mkdir(parents=True, exist_ok=True)
    results: list[BenchResult] = []

    for i, q in enumerate(pending, 1):
        print(f"  [{i}/{len(pending)}] {q.question_id}: {q.question[:80]}...")
        error = None
        try:
            predicted = asyncio.run(_query_one(q.question, kb_dir, model))
        except Exception as exc:
            predicted = ""
            error = str(exc)
            print(f"    query failed: {exc}")

        result = BenchResult(
            question_id=q.question_id,
            question=q.question,
            question_type=q.question_type,
            expected_doc_ids=q.expected_doc_ids,
            predicted=predicted,
            gold_answer=q.gold_answer,
            justification=q.justification,
            answer_facts=q.answer_facts,
            evidence=q.evidence,
            metadata=q.metadata,
            error=error,
        )
        results.append(result)

        with open(results_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")

    return results
