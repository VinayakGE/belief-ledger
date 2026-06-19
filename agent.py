#!/usr/bin/env python3
"""
Hackathon agent -- warm-up scaffold (USGS).

Steps 1-3 implemented. Nothing past step 3. Don't design ahead of what runs.

The loop:
  1. State a belief about a claim, with confidence.            -- done
  2. Commit it: compile predicate, serialize, hash, persist.   -- done
  3. Measure: load committed belief, fetch feed, evaluate,      <- THIS FILE
     write outcome.
  4. On disagreement, weigh claim-wrong vs measurement-wrong.   -- not built
  5. Update the belief publicly ("I was wrong").               -- not built
  6. Pick the next measurement that most reduces uncertainty.  -- not built

Two commands, on purpose:
    python3 agent.py commit            # state + lock a belief (NO fetch)
    python3 agent.py observe           # resolve newest open belief vs LIVE feed
    python3 agent.py observe --feed-file snapshot.json   # ...vs a saved feed

`commit` and `observe` are separate invocations so the ledger can prove the
belief predates the measurement. observe re-verifies the committed hash before
resolving and refuses a belief that was edited after commit.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
import math
import operator
import os
import urllib.request

LEDGER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.jsonl")
DEFAULT_FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
SCHEMA_VERSION = "0.1"

# Single source of truth for the magnitude line. Feeds BOTH the claim text and
# the predicate, so English and executable form cannot drift apart.
M5_THRESHOLD = 5.0


# ---------------------------------------------------------------------------
# Step 1 -- belief
# ---------------------------------------------------------------------------
@dataclass
class Belief:
    claim: str
    confidence: float
    rationale: str
    falsifiable_when: str

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")


M5_PLUS_PER_YEAR = 1500 + 150 + 15           # M5-5.9 ~1500, M6-6.9 ~150, M7+ ~15
LAMBDA_PER_HOUR = M5_PLUS_PER_YEAR / (365.25 * 24)


def p_no_m5_in_one_hour() -> float:
    """Poisson: P(zero M5+ events in a rolling 1-hour window)."""
    return math.exp(-LAMBDA_PER_HOUR)


def step1_state_belief() -> Belief:
    p = p_no_m5_in_one_hour()
    return Belief(
        claim=(f"No earthquake of magnitude >= {M5_THRESHOLD} is present in the "
               "current USGS all_hour feed."),
        confidence=round(p, 3),
        rationale=(
            f"Poisson base rate: ~{M5_PLUS_PER_YEAR} M5+ quakes/year globally "
            f"=> lambda={LAMBDA_PER_HOUR:.3f}/hour => P(zero)={p:.3f}. "
            "Prior from frequency, not a guess."
        ),
        falsifiable_when=(
            f"any feature has properties.mag >= {M5_THRESHOLD} "
            "(USGS path: features[].properties.mag)."
        ),
    )


# ---------------------------------------------------------------------------
# Predicate -- one object, two forms: render() -> str, evaluate() -> bool.
# parse() is the inverse of render(), so the condition EXECUTED at observe time
# is reconstructed from the exact string COMMITTED earlier. Recorded == executed.
# ---------------------------------------------------------------------------
_METRICS = {
    # max magnitude over present features; empty feed -> -inf (belief holds).
    "max_mag": lambda features: max(
        (f["properties"]["mag"] for f in features
         if isinstance(f.get("properties"), dict)
         and f["properties"].get("mag") is not None),
        default=float("-inf"),
    ),
}
_OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}


@dataclass(frozen=True)
class Predicate:
    metric: str
    op: str
    threshold: float

    def render(self) -> str:
        return f"{self.metric} {self.op} {self.threshold}"   # "max_mag < 5.0"

    @classmethod
    def parse(cls, s: str) -> "Predicate":
        metric, op, threshold = s.split()
        if metric not in _METRICS or op not in _OPS:
            raise ValueError(f"unknown predicate: {s!r}")
        return cls(metric=metric, op=op, threshold=float(threshold))

    def metric_value(self, features) -> float:
        return _METRICS[self.metric](features)

    def evaluate(self, features) -> bool:
        return _OPS[self.op](self.metric_value(features), self.threshold)


def compile_predicate(belief: Belief) -> Predicate:
    # Belief holds while max_mag < threshold; falsified at >= threshold.
    return Predicate(metric="max_mag", op="<", threshold=M5_THRESHOLD)


# ---------------------------------------------------------------------------
# Ledger primitives -- canonical JSON, hash-seal, verify, append-only.
# ---------------------------------------------------------------------------
def _canonical(payload: dict) -> str:
    # Stable order, no whitespace, fail loud on inf/nan (would break re-parse).
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def seal(payload: dict, hash_field: str) -> dict:
    """Attach a digest computed over the payload WITHOUT the hash field."""
    digest = sha256(_canonical(payload).encode()).hexdigest()
    return {**payload, hash_field: digest}


def verify(record: dict, hash_field: str) -> bool:
    """Recompute the digest and prove it matches what was stored.
    A record edited after the fact fails here -- the whole point."""
    payload = {k: v for k, v in record.items() if k != hash_field}
    return sha256(_canonical(payload).encode()).hexdigest() == record[hash_field]


def append_to_ledger(record: dict) -> None:
    # Append-only. We never rewrite a line. That rule IS "no rewriting history."
    with open(LEDGER_PATH, "a") as fh:
        fh.write(_canonical(record) + "\n")


def read_ledger() -> list:
    if not os.path.exists(LEDGER_PATH):
        return []
    with open(LEDGER_PATH) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _next_belief_id(entries: list, created_at: datetime) -> str:
    day = created_at.strftime("%Y%m%d")
    seq = 1 + sum(1 for e in entries
                  if e.get("kind") == "commitment"
                  and e.get("belief_id", "").startswith(day))
    return f"{day}_{seq:03d}"


# ---------------------------------------------------------------------------
# Step 2 -- commit (no fetch)
# ---------------------------------------------------------------------------
def do_commit() -> dict:
    created_at = datetime.now(timezone.utc)
    belief = step1_state_belief()
    predicate = compile_predicate(belief)
    entries = read_ledger()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "commitment",
        "belief_id": _next_belief_id(entries, created_at),
        "claim": belief.claim,
        "confidence": belief.confidence,
        "predicate": predicate.render(),
        "created_at": created_at.isoformat(timespec="seconds"),
    }
    record = seal(payload, "commitment_hash")
    append_to_ledger(record)
    ok = verify(record, "commitment_hash")

    print("STEP 1: BELIEF")
    print(f"  claim:      {belief.claim}")
    print(f"  confidence: {belief.confidence}")
    print(f"  rationale:  {belief.rationale}")
    print(f"  wrong when: {belief.falsifiable_when}")
    print()
    print("STEP 2: COMMITMENT")
    print(f"  belief_id:  {record['belief_id']}")
    print(f"  predicate:  {record['predicate']}")
    print(f"  hash:       {record['commitment_hash']}")
    print(f"  created_at: {record['created_at']}")
    print(f"  verified:   {'hash matches' if ok else 'INTEGRITY FAILURE'}")
    print(f"  ledger:     appended to {os.path.basename(LEDGER_PATH)}")
    print()
    print("Belief locked. Run `observe` later to resolve it against the feed.")
    return record


# ---------------------------------------------------------------------------
# Step 3 -- observe: load committed belief, fetch, evaluate, write outcome
# ---------------------------------------------------------------------------
def latest_open_commitment(entries: list):
    resolved = {e["belief_id"] for e in entries if e.get("kind") == "outcome"}
    opens = [e for e in entries
             if e.get("kind") == "commitment" and e["belief_id"] not in resolved]
    return opens[-1] if opens else None     # append-order => last is newest


def fetch_measurement(feed_file=None):
    if feed_file:
        with open(feed_file) as fh:
            raw, source = fh.read(), feed_file
    else:
        with urllib.request.urlopen(DEFAULT_FEED_URL, timeout=15) as resp:
            raw, source = resp.read().decode(), DEFAULT_FEED_URL
    data = json.loads(raw)
    generated = (data.get("metadata") or {}).get("generated")
    feed_time = (datetime.fromtimestamp(generated / 1000, tz=timezone.utc)
                 .isoformat(timespec="seconds")) if generated else None
    return data, source, feed_time


def do_observe(feed_file=None) -> dict:
    entries = read_ledger()
    commitment = latest_open_commitment(entries)
    if commitment is None:
        print("No open commitment to resolve. Run `commit` first.")
        return None
    if not verify(commitment, "commitment_hash"):
        print(f"INTEGRITY FAILURE: belief {commitment.get('belief_id')} was "
              "altered after commit. Refusing to resolve.")
        return None

    try:
        data, source, feed_time = fetch_measurement(feed_file)
    except Exception as exc:
        print(f"Could not read measurement: {exc}")
        print("(Sandbox has no network. Use --feed-file to replay a saved feed.)")
        return None

    features = data.get("features", [])
    # Reconstruct the predicate from the COMMITTED string, then execute it.
    predicate = Predicate.parse(commitment["predicate"])
    value = predicate.metric_value(features)
    held = predicate.evaluate(features)
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "outcome",
        "belief_id": commitment["belief_id"],
        "commitment_hash": commitment["commitment_hash"],  # exact belief resolved
        "predicate": commitment["predicate"],
        "observed_at": observed_at,
        "measurement": {
            "source": source,
            "feed_generated_at": feed_time,
            "feature_count": len(features),
            "metric": predicate.metric,
            "metric_value": value if value != float("-inf") else None,
        },
        "held": held,
    }
    record = seal(payload, "outcome_hash")
    append_to_ledger(record)

    shown = record["measurement"]["metric_value"]
    print("STEP 3: MEASUREMENT + OUTCOME")
    print(f"  resolving:   {record['belief_id']}  "
          f"(commitment {commitment['commitment_hash'][:12]}...)")
    print(f"  integrity:   committed belief verified (hash matches)")
    print(f"  source:      {source}")
    print(f"  feed time:   {feed_time}")
    print(f"  features:    {len(features)}")
    print(f"  predicate:   {record['predicate']}   ->   "
          f"{predicate.metric} = {shown}")
    print(f"  held:        {'TRUE  (belief survived the measurement)' if held else 'FALSE (measurement contradicts the belief)'}")
    print(f"  observed_at: {observed_at}")
    print(f"  outcome:     appended, hash {record['outcome_hash'][:12]}...")
    print()
    print("Chain complete: belief -> commitment -> measurement -> outcome.")
    print("No adjudication, no update. That's steps 4-5, not built yet.")
    return record


def main():
    p = argparse.ArgumentParser(description="commitment-ledger agent (USGS warm-up)")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("commit", help="state and lock a belief (no fetch)")
    obs = sub.add_parser("observe", help="resolve newest open belief vs the feed")
    obs.add_argument("--feed-file", help="resolve against a saved feed snapshot")
    args = p.parse_args()

    if args.cmd == "observe":
        do_observe(args.feed_file)
    else:
        do_commit()       # default


if __name__ == "__main__":
    main()
