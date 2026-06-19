#!/usr/bin/env python3
"""
Scoring dashboard for ledger analysis.

Computes:
- runs_completed
- correct (held)
- incorrect (failed)
- accuracy
- confidence_distribution

Usage:
    python3 score_dashboard.py [ledger_file]
"""

import json
import sys
from collections import defaultdict


def analyze_ledger(ledger_path: str) -> dict:
    """Compute accuracy and calibration metrics."""
    if not open(ledger_path):
        return {"error": f"Ledger not found: {ledger_path}"}

    entries = []
    with open(ledger_path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    # Filter to completed cycles (commitment + outcome)
    outcomes = [e for e in entries if e.get("kind") == "outcome"]
    commitments = {e["belief_id"]: e for e in entries if e.get("kind") == "commitment"}

    held = sum(1 for o in outcomes if o.get("held"))
    failed = len(outcomes) - held
    accuracy = held / len(outcomes) if outcomes else 0.0

    # Confidence distribution
    confidence_dist = defaultdict(int)
    for belief_id, o in zip([e["belief_id"] for e in outcomes], outcomes):
        if belief_id in commitments:
            conf = commitments[belief_id].get("confidence", 0.0)
            conf_bin = round(conf * 10) / 10  # 0.0, 0.1, 0.2, ...
            confidence_dist[conf_bin] += 1

    return {
        "runs_completed": len(outcomes),
        "correct": held,
        "incorrect": failed,
        "accuracy": round(accuracy, 3),
        "confidence_distribution": dict(sorted(confidence_dist.items())),
        "expected_accuracy_at_0_827": 0.827,
    }


def main():
    ledger = sys.argv[1] if len(sys.argv) > 1 else "ledger.jsonl"
    metrics = analyze_ledger(ledger)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
