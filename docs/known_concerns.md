# Known Concerns

Record of observations and critiques that are valid but not actionable now.

These are deferred until specified review triggers, to preserve the frozen experiment loop.

---

## KC-001: Observable Saturation Risk

**Date:** 2026-06-20

**Title:** Binary Belief May Operate in Saturated Regime

**Observation:**

Current 7-day belief: P(no M5+ earthquake in next 7 days) ≈ 0.827

Scoring: Binary outcome (Held / Failed)

**Problem:**

M5+ events are sufficiently rare that the expected held rate over 100 runs approaches 95%+.

Two materially different rate models:
- λ = 31.9 events/7 days
- λ = 26.9 events/7 days

...produce identical binary outcomes (almost always Held=True).

The binary observable destroys information about model quality differences.

**Consequence:**

100 correctly scored cycles may accumulate while learning little about whether the confidence estimate (0.827) is calibrated.

**Status:** Deferred

**Review Trigger:** After first 100 immutable scored cycles

**Action:** None now. At Run #100, evaluate whether:
1. Outcome variance is sufficient for calibration analysis
2. Alternative observables (count-based, threshold-based) would be informative
3. Belief redesign is warranted before Run #1000

---

## Decision Log

**2026-06-20:**
Concern recorded. Freeze maintained. No code changes.
