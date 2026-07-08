# Reference Experiment 001
## Earthquake Commitment Loop

**Period:** 2026-06-19 to 2026-07-08  
**Cycles completed:** 175  
**Commit:** e15fdc5  
**Status:** Complete. Archived.

---

## Experimental Design

**Belief:** No earthquake of magnitude ≥ 5.0 present in the USGS all_hour feed.  
**Confidence:** 0.827 (fixed, never updated)  
**Observable:** max magnitude in USGS all_hour GeoJSON feed  
**Falsification condition:** any feature with properties.mag ≥ 5.0  
**Cycle frequency:** hourly (GitHub Actions cron)  
**Ledger:** append-only JSONL, SHA-256 sealed entries

---

## Results

| Metric | Value |
|--------|-------|
| Runs completed | 175 |
| Held | 150 |
| Failed | 25 |
| Orphans | 0 |
| Observed accuracy | 85.7% |
| Expected accuracy (confidence=0.827) | 82.7% |
| Failure taxonomy categories | 1 |
| Scheduler disruptions | 0 |
| Ledger integrity failures | 0 |

**Failure magnitudes observed:** 5.0–6.1 (all M5+, consistent with falsification condition)

---

## Research Questions and Evidence

| Research Question | Evidence | Conclusion |
|-------------------|----------|------------|
| Can a commitment loop run autonomously over long periods? | 175 runs, 0 orphans, 19 days continuous operation | Supported |
| Does this domain naturally produce multiple failure taxonomies? | 25 failures, taxonomy remained 1 throughout | Not observed |
| Did operational reliability degrade over time? | Scheduler and ledger remained healthy from Run 1 to Run 175 | Not observed |
| Did human memory become insufficient to track failures? | All 25 failures held in working memory without pressure | Not observed |
| Did attribution pressure emerge? | No failure required explanation beyond "reality contradicted belief" | Not observed |

---

## What Was Not Claimed

- Step 4 (attribution) is unnecessary everywhere.
- This domain will never generate attribution pressure under any conditions.
- The candidate method is universal.
- The confidence estimate (0.827) is calibrated.

Each of the above requires evidence this experiment did not produce.

---

## Central Finding

> After 175 autonomous contacts with reality, no second failure taxonomy emerged.

A commitment loop without adaptive behavior remained operationally stable for 175 cycles. Every failure belonged to a single category: reality contradicted belief. No failure required explanation. No failure exceeded working memory. The current layer did not demonstrably lose information.

This is a finding about this domain under these conditions. It is not a finding about domains generally.

---

## Decision Rule Supported by This Experiment

> Never add a layer because it seems useful. Add it only when repeated contact with reality demonstrates that the current layer is losing information or making systematically worse decisions.

This rule governed every decision from Run 1 to Run 175. It has not been falsified.

---

## Known Concerns (Deferred, Now Recorded)

**KC-001 (Observable Saturation Risk):** The binary observable (held/failed) may not distinguish between models with meaningfully different failure rates. This experiment did not test calibration — it tested operational stability. A calibration analysis would require count-based observables and a different experimental design.

This concern was recorded at Run 0 and remains valid. It does not invalidate the central finding, which was never about calibration.

---

## Archive Notes

- `agent.py`: unchanged from final production state
- `ledger.jsonl`: append-only, 175 completed cycles, immutable
- `.github/workflows/ledger-cycle.yml`: scheduler disabled (cron removed), workflow preserved
- This repository is the reference baseline for future experiments

---

## Next

**Reference Experiment 002** should be designed specifically to challenge the conclusions of this experiment.

Objective: choose a domain expected to produce multiple competing failure modes, ambiguity, or recurring explanations — to test whether attribution pressure is domain-dependent.

If Experiment 002 also produces taxonomy=1, the candidate method strengthens.  
If Experiment 002 produces taxonomy>1, the boundary where Stage 2 begins has been found.

Either outcome advances the research.
