# belief-ledger — Reference Experiment 001

**Status: Complete.** 175 autonomous cycles. Archived 2026-07-08.

A commitment-ledger agent (USGS earthquake warm-up). It states a falsifiable
belief, seals it with a SHA-256 hash *before* measuring, fetches the live feed,
and records whether the belief held — append-only, in `ledger.jsonl`.

## Final results

| Metric | Value |
|--------|-------|
| Runs completed | 175 |
| Held | 150 |
| Failed | 25 |
| Orphans | 0 |
| Observed accuracy | 85.7% |
| Failure taxonomy | 1 |

Full report: [`docs/reference-experiment-001.md`](docs/reference-experiment-001.md)

## What this experiment answered

> After 175 autonomous contacts with reality, no second failure taxonomy emerged.

The loop ran unattended for 19 days. Every failure belonged to one category:
reality contradicted belief. No failure required explanation. No attribution
layer was earned.

## What it did not claim

- That attribution is unnecessary everywhere
- That this domain will never generate complexity
- That the method generalises beyond this experiment

## Run one cycle locally

    python3 agent.py commit     # state + seal a belief (no fetch)
    python3 agent.py observe    # fetch live USGS feed, resolve the belief

Both append to `ledger.jsonl`. Pure standard library, Python 3.8+.
No network handy? `python3 agent.py observe --feed-file saved_feed.json` replays a snapshot.

## Scheduler

Disabled at Run 175. The workflow file
`.github/workflows/ledger-cycle.yml` is preserved so the experiment can be
restarted under identical conditions via **Actions → Run workflow**.

## Peek at the ledger

    python3 -c "import json; o=[r for r in map(json.loads, open('ledger.jsonl')) if r['kind']=='outcome']; print(sum(r['held'] for r in o), '/', len(o), 'held')"
