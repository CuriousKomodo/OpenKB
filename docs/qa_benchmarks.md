# Document QA Benchmarks

## EnterpriseRAG-Bench

- **Paper:** [EnterpriseRAG-Bench: A RAG Benchmark for Company Internal Knowledge](https://arxiv.org/html/2605.05253v2)
- **Dataset:** 500 questions over synthetic enterprise documents
- **Public:** Yes
- **GitHub:** https://github.com/onyx-dot-app/EnterpriseRAG-Bench
- **Dataset download:** https://github.com/onyx-dot-app/EnterpriseRAG-Bench/releases/latest
- **Leaderboard:** https://huggingface.co/spaces/onyx-dot-app/EnterpriseRAG-Bench-Leaderboard

Includes full corpus, questions JSONL, generation pipeline code, and evaluation harness.

## FinanceBench

- **Paper:** [FinanceBench: A New Benchmark for Financial Question Answering](https://arxiv.org/abs/2311.11944)
- **Dataset:** 10,231 questions about publicly traded companies; open-source sample of 150 annotated examples
- **Public:** Yes (150-example open sample)
- **GitHub:** https://github.com/patronus-ai/financebench
- **HuggingFace:** https://huggingface.co/datasets/PatronusAI/financebench

Expert-written financial QA grounded in real SEC filings (10-Ks, 10-Qs, 8-Ks, earnings reports). Documents are PDFs. Each example includes the question, gold answer, evidence string, and source document. GPT-4-Turbo with retrieval incorrectly answered 81% of questions in the original evaluation.

## AMAQA

- **Paper:** [AMAQA: A Metadata-based QA Dataset for RAG Systems](https://arxiv.org/html/2505.13557v2)
- **Dataset:** ~1.1M Telegram messages + 20K hotel reviews, 2,600 QA pairs
- **Public:** Yes (open-access)
- **GitHub:** https://github.com/DavideBruni/AMAQA
- **Source data:** https://www.kaggle.com/datasets/datafiniti/hotel-reviews (hotel reviews)

Focuses on metadata-aware QA — questions that require filtering/reasoning over message or review metadata.

## MRAG-Bench

- **Paper:** [MRAG: Benchmarking Retrieval-Augmented Generation for Bio-medicine](https://arxiv.org/html/2601.16503v1)
- **Dataset:** Biomedical RAG benchmark
- **Public:** Not yet — dataset and toolkit to be released upon paper acceptance.
- **GitHub:** None provided yet.
