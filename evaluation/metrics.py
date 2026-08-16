import math
from typing import List, Set, Dict, Any

def recall_at_k(retrieved_ids: List[str], ground_truth_ids: Set[str], k: int = 5) -> float:
    if not ground_truth_ids:
        return 1.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for cid in top_k if cid in ground_truth_ids)
    return 1.0 if hits > 0 else 0.0

def mean_reciprocal_rank(retrieved_ids: List[str], ground_truth_ids: Set[str]) -> float:
    if not ground_truth_ids:
        return 1.0
    for rank, cid in enumerate(retrieved_ids):
        if cid in ground_truth_ids:
            return 1.0 / (rank + 1)
    return 0.0

def ndcg_at_k(retrieved_ids: List[str], ground_truth_ids: Set[str], k: int = 5) -> float:
    if not ground_truth_ids:
        return 1.0
    dcg = 0.0
    for rank, cid in enumerate(retrieved_ids[:k]):
        rel = 1.0 if cid in ground_truth_ids else 0.0
        dcg += rel / math.log2(rank + 2)
    idcg = 1.0 / math.log2(2)
    return dcg / idcg

def compute_abstention_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    tp = sum(1 for r in results if r["should_abstain"] and r["abstained"])
    fp = sum(1 for r in results if not r["should_abstain"] and r["abstained"])
    fn = sum(1 for r in results if r["should_abstain"] and not r["abstained"])
    tn = sum(1 for r in results if not r["should_abstain"] and not r["abstained"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    accuracy = (tp + tn) / len(results) if results else 1.0

    return {
        "abstention_precision": round(precision, 3),
        "abstention_recall": round(recall, 3),
        "abstention_accuracy": round(accuracy, 3)
    }
