---
id: T08
title: Robust + canonical polarized-element computation (upstream issue #5)
status: open
owner: none
priority: P0
tier: 1
repos: [ShimCurve]
depends_on: []
questions: [Q3]
---

## Context

Upstream issue assaferan/ShimCurve#5: `HasPolarizedElementOfDegree` (`code/level-structure/polarization-twisting.m:71`) is ad hoc. Problems: Magma's `Embed` is non-deterministic and sometimes returns μ with enormous coefficients; `InternalConjugatingElement` errors on non-maximal Eichler orders; the Eichler fallback is a naive point search. Consequences: irreproducible stored `mu` / `AutmuO_generators` coordinates (cf. T06's 800-vs-804 row drift), fragility that blocks Eichler-order level structure (T22), and slow/failed searches at larger discriminant.

A μ of degree d is an element of O with μ² + d·disc(O) = 0, i.e. a trace-zero element with nrd(μ) = d·disc(O).

## Task

A deterministic, always-terminating (within the target range), canonical computation of μ for maximal and Eichler orders, per Q3's canonical-form decision.

## Steps

1. Read Q3. If no canonical form is prescribed, propose one in this ticket's Log and get sign-off before mass regeneration (suggested default: enumerate trace-zero short vectors of the positive-definite form nrd on O⁰ ∩ (lattice), take the first vector of norm d·disc(O) under a fixed ordering — deterministic by construction).
2. Implement: restrict nrd to the rank-3 trace-zero sublattice O⁰ (basis via `TraceZeroSubspace`-style computation from the O-basis), run `ShortVectors` / `ThetaSeries`-guided enumeration up to d·disc(O), filter nrd = d·disc(O) exactly. This avoids `Embed` entirely. Keep the old path behind a flag for comparison.
3. Preserve the intrinsic's contract: same signature and return convention (`tr, mu`), same downstream expectations (`DegreeOfPolarizedElement(O,mu)` = d at `:154`; `IsTwisting`; `Aut(O,mu)` — run these on the new μ for the full D ≤ 1000 maximal range as a consistency sweep).
4. Handle the twisting subtleties: `polarization-twisting.m:196` has "TODO: not sure if this is enough when O is not maximal to conclude element is in normalizer" — resolve for Eichler orders (the normalizer condition must be *checked*, not assumed; add the check).
5. Determinism test: run the sweep twice, assert identical μ coordinates. Speed: record timings; D ≤ 1000, all degrees, should be minutes not hours (short-vector enumeration in rank 3 is fast).
6. Regenerate `quaternion-orders-polarized` files; expect coordinate-level diffs everywhere (that's the point) — verify invariants (`deg_mu`, `nrd_mu`, `AutmuO_size`, `AutmuO_label`) are unchanged row-by-row vs old files, and flag any row where they differ (that would be a real bug being fixed — investigate each).
7. Tests: extend `tests/smoke_intrinsics.m` with a determinism assertion; `run_quick.m` green. Stage reload commands in the Log.
8. Draft (don't post) the upstream issue #5 resolution comment.

## Acceptance criteria

- No call path into `Embed`/`InternalConjugatingElement` remains in polarized-element computation (grep proof).
- Determinism sweep passes; invariant comparison old-vs-new documented.
- Eichler orders: `HasPolarizedElementOfDegree` succeeds for all Eichler orders with discO ≤ 1000, deg 1 (the current 86-row range) and a sample of higher degrees.

## Log

- 2026-07-16: ticket created from survey.
