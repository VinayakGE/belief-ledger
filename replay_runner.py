#!/usr/bin/env python3
"""
Historical replay runner.

Same belief-commit-observe loop, but:
- Data source: historical earthquake dataset (CSV)
- Timing: chronological, reveal 7-day windows
- Purpose: accumulate 100s-1000s of cycles for calibration analysis

Usage:
    python3 replay_runner.py /data/earthquakes_2021.csv
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import argparse
import csv
import json
import os

LEDGER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger_replay.jsonl")
SCHEMA_VERSION = "0.1"
M5_THRESHOLD = 5.0
FORECAST_WINDOW_DAYS = 7


@dataclass
class ReplayEvent:
    magnitude: float
    time: datetime


def load_historical_data(csv_path: str) -> list:
    """Load earthquakes from CSV. Expected columns: time, magnitude"""
    events = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                time = datetime.fromisoformat(row['time'].replace('Z', '+00:00'))
                mag = float(row['magnitude'])
                events.append(ReplayEvent(magnitude=mag, time=time))
            except (ValueError, KeyError):
                continue
    return sorted(events, key=lambda e: e.time)


def generate_belief_at_time(observation_time: datetime) -> dict:
    """Generate a belief at a specific point in time."""
    return {
        "claim": f"No earthquake of magnitude >= {M5_THRESHOLD} will occur in the next {FORECAST_WINDOW_DAYS} days.",
        "confidence": 0.827,
        "falsification_condition": f"any earthquake with magnitude >= {M5_THRESHOLD} occurs before {(observation_time + timedelta(days=FORECAST_WINDOW_DAYS)).isoformat()}",
        "expiry": (observation_time + timedelta(days=FORECAST_WINDOW_DAYS)).isoformat(),
        "rationale": "Base rate: ~1665 M5+ quakes/year globally.",
    }


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def seal(payload: dict, hash_field: str) -> dict:
    digest = sha256(_canonical(payload).encode()).hexdigest()
    return {**payload, hash_field: digest}


def append_to_ledger(record: dict) -> None:
    with open(LEDGER_PATH, "a") as fh:
        fh.write(_canonical(record) + "\n")


def run_replay(csv_path: str, max_cycles: int = None):
    """
    Replay historical data cycle by cycle.

    For each point in time:
    - Generate a belief (locked before measurement)
    - Reveal the next N days
    - Score the outcome
    - Append to ledger
    """
    events = load_historical_data(csv_path)
    if not events:
        print(f"No events loaded from {csv_path}")
        return

    # Generate observation points (every 7 days)
    start_time = events[0].time
    end_time = events[-1].time - timedelta(days=FORECAST_WINDOW_DAYS)

    current_time = start_time
    cycle_count = 0

    while current_time < end_time and (max_cycles is None or cycle_count < max_cycles):
        # Generate belief at this moment
        belief = generate_belief_at_time(current_time)
        forecast_end = current_time + timedelta(days=FORECAST_WINDOW_DAYS)

        # Commit belief
        commitment = {
            "schema_version": SCHEMA_VERSION,
            "kind": "commitment",
            "belief_id": f"replay_{current_time.strftime('%Y%m%d_%H%M')}",
            "claim": belief["claim"],
            "confidence": belief["confidence"],
            "falsification_condition": belief["falsification_condition"],
            "expiry": belief["expiry"],
            "created_at": current_time.isoformat(timespec="seconds"),
        }
        commitment = seal(commitment, "commitment_hash")
        append_to_ledger(commitment)

        # Score: check if any M5+ events occur in the window
        events_in_window = [e for e in events if current_time <= e.time < forecast_end]
        max_mag = max((e.magnitude for e in events_in_window), default=float("-inf"))
        held = max_mag < M5_THRESHOLD

        # Record outcome
        outcome = {
            "schema_version": SCHEMA_VERSION,
            "kind": "outcome",
            "belief_id": commitment["belief_id"],
            "commitment_hash": commitment["commitment_hash"],
            "falsification_condition": belief["falsification_condition"],
            "observed_at": current_time.isoformat(timespec="seconds"),
            "measurement": {
                "source": csv_path,
                "window_start": current_time.isoformat(),
                "window_end": forecast_end.isoformat(),
                "event_count": len(events_in_window),
                "max_magnitude": max_mag if max_mag != float("-inf") else None,
            },
            "held": held,
        }
        outcome = seal(outcome, "outcome_hash")
        append_to_ledger(outcome)

        cycle_count += 1
        if cycle_count % 50 == 0:
            print(f"Completed {cycle_count} cycles...")

        # Advance 7 days
        current_time += timedelta(days=FORECAST_WINDOW_DAYS)

    print(f"Replay complete: {cycle_count} cycles")
    return cycle_count


def main():
    p = argparse.ArgumentParser(description="Replay historical earthquakes through belief ledger")
    p.add_argument("csv_file", help="Path to earthquake CSV (columns: time, magnitude)")
    p.add_argument("--max-cycles", type=int, default=None, help="Limit number of cycles")
    args = p.parse_args()

    run_replay(args.csv_file, args.max_cycles)


if __name__ == "__main__":
    main()
