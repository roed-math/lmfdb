---
id: T19
title: Generalize NormalizerPlusGenerators beyond D ∈ {6, 10, 15}
status: open
owner: none
priority: P1
tier: 3
repos: [ShimCurve]
depends_on: []
questions: [Q8]
---

## Context

`NormalizerPlusGenerators(O)` (`code/level-structure/elliptic-elements.m:2-55`) returns **hardcoded** generator lists of N_{Bˣ}(O)⁺/ℚˣ for the maximal orders of D = 6, 10, 15, and the string `"oops, not written for this discriminant yet"` otherwise. Everything scales through it: `NormalizerPlusGeneratorsEnhanced` (`polarization-twisting.m:157`), `GetG1plus` (`enumerate-H.m:40`), `EnhancedEllipticElements` (`elliptic-elements.m:199`), hence the entire enhanced enumeration. This is blocker #1 for any discriminant beyond {6,10,15} (blocker #2 is T20).

Q8 decides the method. The natural general route: Magma's `FuchsianGroup(O)` computes a fundamental domain and generators of the unit group Γ⁰(O) (norm-1); AL/normalizer representatives for each m ∥ D·M come from elements of norm m in O normalizing O. Expensive but cacheable.

## Steps

1. Read Q8. Implement `NormalizerPlusGenerators(O)` generally:
   - norm-1 part: `FuchsianGroup(QuaternionAlgebra(O))` / `Group(...)` side-generators (check Magma docs `FuchsianGroup`, `Generators`), pulled back to O-elements;
   - AL part: for each m ∥ disc(O)·level, find x ∈ O with nrd(x) = m and x·O·x⁻¹ = O (short-vector search on the norm form, reusing T08's enumeration machinery; positivity of norm automatic since B is indefinite and nrd(x)=m>0).
   - Constraints from Q8.2 (whatever the enhanced wrapper needs — inspect how the current hardcoded lists are consumed by `NormalizerPlusGeneratorsEnhanced` before choosing output normalization).
2. **Regression gate**: for D = 6, 10, 15 the new code must generate the **same subgroup** of Bˣ/ℚˣ as the hardcoded lists (not necessarily the same generators): verify by comparing the generated enhanced images G1plus in GL₄(ℤ/N) for N = 3, 4 — identical groups. Keep the hardcoded lists as a test oracle, not as the code path.
3. Cache: persist computed generators per order label under `data/normalizer-gens/` (Magma-readable), keyed by order label, with a loader that recomputes on miss. FuchsianGroup at D ~ 1000 may take minutes — record timings for D ∈ {6,10,15,21,22,26,33,…,~200} in the Log.
4. Smoke the downstream: run `GenerateDataForGerbiestSurjectiveH` for D=10, deg 1, N=3 end-to-end (it will hit T20's elliptic-point limitation — for this ticket, stub the ν-columns as NULL if T20 isn't done; genus via Riemann–Hurwitz still works since `EnhancedGenus(sigma)` is general).
5. Tests: add D=10 generator-subgroup regression to `tests/`.

## Acceptance criteria

- D ∈ {6,10,15}: generated == hardcoded (as subgroups), asserted in tests.
- D = 21 (next discriminant, not hardcoded): generators produced, `EnhancedImageGL4`/`GetG1plus` run, index-2 (or per-T10 corrected) relation holds at N=3.
- Timing table in the Log; cache round-trips.

## Log

- 2026-07-16: ticket created from survey.
