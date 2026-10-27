"""Phase 3 evaluation primitives. Uses B's JSONL labels and real Agent outputs."""
from __future__ import annotations

import json
from pathlib import Path


def _f1(precision, recall):
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def score_sets(expected, actual):
    expected, actual = set(expected), set(actual)
    tp = len(expected & actual); fp = len(actual - expected); fn = len(expected - actual)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(_f1(precision, recall), 4)}


def evaluate_questions(records, answer_fn):
    """records are B's questions.jsonl rows; answer_fn(row) returns Agent answer dict."""
    answerable = []; unanswerable = []; cited = []
    for row in records:
        result = answer_fn(row)
        expected = set(row.get("expected_chunk_ids", []))
        actual = {x.get("chunk_id") for x in result.get("citations", [])}
        is_answerable = row.get("answerable", True)
        supported = bool(expected & actual) if expected else not result.get("abstained", False)
        (cited if is_answerable else unanswerable).append(supported if is_answerable else result.get("abstained", False))
    return {
        "answer_support_rate": round(sum(cited) / len(cited), 4) if cited else 0.0,
        "abstention_accuracy": round(sum(unanswerable) / len(unanswerable), 4) if unanswerable else 0.0,
        "answerable_count": len(answerable), "unanswerable_count": len(unanswerable),
    }


def evaluate_dataset(path, answer_fn):
    rows = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    return {"dataset": str(path), "question_count": len(rows), "metrics": evaluate_questions(rows, answer_fn)}


def pass_gate(metrics):
    gates = {
        "answer_support_rate": metrics.get("answer_support_rate", 0) >= 0.90,
        "abstention_accuracy": metrics.get("abstention_accuracy", 0) >= 0.85,
    }
    return {"pass": all(gates.values()), "gates": gates}
