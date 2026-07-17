---
id: T20
title: Generalize elliptic-point counting beyond D=6
status: open
owner: none
priority: P1
tier: 3
repos: [ShimCurve]
depends_on: [T19]
questions: [Q7]
---

## Context

`EnhancedEllipticPoints(sigma)` (`code/level-structure/genera.m:18-34`) is documented **"Only works for discriminant 6!"**: it assumes the ramification triple σ is indexed by three branch points of orders `bottom := [2,4,6]` — i.e. that the bottom orbifold (quotient of X(D;1) by the full enhanced normalizer-plus group) is the (2,4,6)-triangle for D=6/deg 1. The ν₂/ν₃/ν₄/ν₆ columns are only correct under that assumption; even D=10/15 (unlocked by T19) would be wrong. Note `EnhancedGenus` (`genera.m:4`) is already general (pure Riemann–Hurwitz) — only the ν-bucketing is D=6-specific. Also note `RamificationData`/`EnhancedRamificationData` (`enumerate-H.m:171`, `genera.m`) produce σ **relative to the same assumed bottom** — the generalization must produce (bottom signature, σ over its branch points) as a pair.

Q7 decides the mathematical route (Ogg-style counting as in `X0DN_code.m` extended to the enhanced quotient, vs. computing the Fuchsian signature of the bottom group directly) and the schema question (can ν-orders other than 2,3,4,6 occur → list-of-pairs column?).

## Steps

1. Compute the bottom signature generally: given O, μ (and T19's generators), determine the signature of Γ = image of the enhanced normalizer-plus group — candidates: (a) Magma `FuchsianGroup` signature of the group generated (if representable); (b) formula: start from the signature of Γ⁰(D·M) (classical, `SignatureX0DN` in `X0DN_code.m`) and account for the Aut_{±μ}(O)-quotient via fixed-point counts (`OggCountFixedPoints`, `SignatureX0DNmodAtkinLehnerElement` at `code/tables/signatures_single_AL_element_X0DN.m:186` already do single-element AL quotients — the needed extension is quotients by the full subgroup W ≤ Aut, composing fixed-point data via Burnside/Riemann–Hurwitz through the tower). Follow Q7.1.
2. Rework the σ plumbing: `EnhancedRamificationData` should return σ indexed by the computed bottom branch points (arbitrary count k, orders e₁..e_k, plus bottom genus g₀); `EnhancedGenus` gets the (g₀, orders) as input (RH with 2g₀−2 base term — currently hardcoded −2·d? check line `rhs := -2*d + ...` assumes g₀=0: generalize).
3. ν-columns: per Q7.3, either keep ν₂/ν₃/ν₄/ν₆ and assert no other orders occur in scope, or migrate schema to `elliptic_orders integer[]` pairs (coordinate with T04's canonical schema and note the frontend display `web_curve.py:657`, `main.py:601-604` reads nu2..nu6).
4. Validation battery:
   - D=6 corpus regenerates **identically** (all 2,198 rows byte-equal on genus + ν columns).
   - Coarse checks: for the trivial H at (D,N) with deg 1, genus and e₂/e₃ must match `SignatureX0DN(D,N)` for D ∈ {6,10,15,21,26}, N ∈ {1,3} (X0DN_code is the independent oracle).
   - Gauss–Bonnet: the existing area assert (`enumerate-H.m:280-283`) generalizes — keep it on.
5. Tests: add a D=10 genus/ν regression case with the oracle values.

## Acceptance criteria

- D=6 byte-identical regeneration; oracle agreement for D ∈ {10,15,21,26}; area assertion holds corpus-wide.
- Documented decision (with Q7) on the ν-schema.

## Log

- 2026-07-16: ticket created from survey.
