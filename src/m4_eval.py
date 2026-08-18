from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset

        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })
        result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision, context_recall])
        df = result.to_pandas()
        per_question = []
        for _, row in df.iterrows():
            f_val = row.get("faithfulness", 0.0)
            ar_val = row.get("answer_relevancy", 0.0)
            cp_val = row.get("context_precision", 0.0)
            cr_val = row.get("context_recall", 0.0)
            per_question.append(EvalResult(
                question=str(row["question"]),
                answer=str(row["answer"]),
                contexts=row["contexts"] if isinstance(row["contexts"], list) else [str(row["contexts"])],
                ground_truth=str(row["ground_truth"]),
                faithfulness=float(f_val) if f_val is not None and str(f_val) != "nan" else 0.0,
                answer_relevancy=float(ar_val) if ar_val is not None and str(ar_val) != "nan" else 0.0,
                context_precision=float(cp_val) if cp_val is not None and str(cp_val) != "nan" else 0.0,
                context_recall=float(cr_val) if cr_val is not None and str(cr_val) != "nan" else 0.0,
            ))
        return {
            "faithfulness": float(result.get("faithfulness", 0.0) or 0.0),
            "answer_relevancy": float(result.get("answer_relevancy", 0.0) or 0.0),
            "context_precision": float(result.get("context_precision", 0.0) or 0.0),
            "context_recall": float(result.get("context_recall", 0.0) or 0.0),
            "per_question": per_question,
        }
    except Exception as e:
        print(f"  ⚠️  RAGAS evaluation failed: {e}")
        per_question = [
            EvalResult(
                question=q, answer=a, contexts=c, ground_truth=gt,
                faithfulness=0.0, answer_relevancy=0.0, context_precision=0.0, context_recall=0.0,
            )
            for q, a, c, gt in zip(questions, answers, contexts, ground_truths)
        ]
        return {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "per_question": per_question,
        }


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    if not eval_results:
        return []
    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating / Output inconsistent with context", "Tighten prompt constraints, lower temperature, ensure retrieved chunks contain factual data"),
        "context_recall": ("Missing relevant chunks in retrieved context", "Improve chunking strategy, switch to hierarchical chunking or combine BM25 and Dense with RRF"),
        "context_precision": ("Too many irrelevant chunks or low ranking of target chunks", "Add cross-encoder reranking, filter low-scoring documents, or add metadata filtering"),
        "answer_relevancy": ("Answer does not directly address the question", "Improve system prompt instructions, refine query reformulation or HyDE"),
    }
    scored = []
    for r in eval_results:
        metrics = {
            "faithfulness": r.faithfulness,
            "answer_relevancy": r.answer_relevancy,
            "context_precision": r.context_precision,
            "context_recall": r.context_recall,
        }
        avg_score = sum(metrics.values()) / 4.0
        worst_m = min(metrics.keys(), key=lambda k: metrics[k])
        scored.append((avg_score, worst_m, metrics[worst_m], r))

    scored.sort(key=lambda x: x[0])
    failures = []
    for avg_score, worst_m, worst_val, r in scored[:bottom_n]:
        diag, fix = diagnostic_tree.get(worst_m, ("Unknown issue", "Review pipeline configuration"))
        failures.append({
            "question": r.question,
            "answer": r.answer,
            "ground_truth": r.ground_truth,
            "worst_metric": worst_m,
            "score": round(float(worst_val), 4),
            "average_score": round(float(avg_score), 4),
            "diagnosis": diag,
            "suggested_fix": fix,
        })
    return failures


def save_report(results: dict, failures: list[dict], path: str = "ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
