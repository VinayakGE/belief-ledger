# subquake-ledger

A commitment-ledger agent (USGS earthquake warm-up). It states a falsifiable
belief, seals it with a SHA-256 hash *before* measuring, fetches the live feed,
and records whether the belief held — append-only, in `ledger.jsonl`.

## Run one cycle locally
    python3 agent.py commit     # state + seal a belief (no fetch)
    python3 agent.py observe    # fetch live USGS feed, resolve the belief

Both append to `ledger.jsonl`. Pure standard library, Python 3.8+.
No network handy? `python3 agent.py observe --feed-file saved_feed.json` replays a snapshot.

## Automated hourly
`.github/workflows/ledger-cycle.yml` runs commit+observe every hour and pushes the
updated ledger back to the repo (using the built-in `GITHUB_TOKEN` — no secret needed).
Trigger it once from the **Actions** tab → **Run workflow** to confirm a clean live
cycle, then leave it alone.

## Rules for this experiment (Milestone A: 100 clean cycles)
1. Do not improve the agent.
2. Do not improve the observer.
3. Do not improve the analysis.
4. Improve sample size.

Changing `agent.py` mid-run forks the experiment. If you must change it, bump
`schema_version` first so the epoch boundary is marked, not silent.

## Peek at the ledger (a glance, not a tool)
    python3 -c "import json; o=[r for r in map(json.loads, open('ledger.jsonl')) if r['kind']=='outcome']; print(sum(r['held'] for r in o), '/', len(o), 'held')"
