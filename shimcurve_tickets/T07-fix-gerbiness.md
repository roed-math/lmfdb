---
id: T07
title: Fix gerbiness computations (upstream issue #6)
status: open
owner: none
priority: P0
tier: 1
repos: [ShimCurve]
depends_on: []
questions: [Q2]
---

## Context

Upstream issue assaferan/ShimCurve#6: the gerbiness computation is wrong — "does not look at the projection onto the Aut_{±μ}(O) factor. The size of the gerbiness should be one when the degree of polarization is 1, but can be larger more generally."

Two code sites compute gerbiness-type data independently:

1. `code/level-structure/enumerate-H.m` (`createRecord`, ~`:246-248`): `gerbiness := #KG_level` where KG comes from `SemidirectToNormalizerKernel(O,mu)` (`code/level-structure/polarization-twisting.m:69`, wrapped by `GetKernelAsSubgroup` at `enumerate-H.m:49`); `aut_gerbiness :=` number of distinct Aut-components among KG's elements. Both columns are 100% populated in the DB (samples: deg 1 → gerbiness 2, aut_gerbiness 1; deg 2 → 4/2; deg 6 → 4/2 or 6/3) — so at least one of these disagrees with the issue's claim that deg 1 ⟹ gerbiness 1. That discrepancy is exactly what Q2 must resolve (definition mismatch vs computational bug).
2. `code/quaternion_orders/enumerate-O.m:258-260` (`LMFDBRowEntry(O,mu)`): hardcodes `Gerby_gen` = identity with the comment "gerbiness = 1 because f: Aut_{±mu}(O) → N_{Bˣ}(O)/Qˣ is injective — only correct when the degree of polarization is 1! TODO: handle this more generally." This is the site the issue links.

## Task

Once Q2 pins the definitions: implement them correctly in both sites, add asserted sanity checks, regenerate affected columns.

## Steps

1. Read Q2's answer. Write the definitions as docstrings on the relevant intrinsics (this is the lasting spec).
2. Implement `Gerby_gen` for deg μ > 1 in `LMFDBRowEntry(O,mu)`: compute the kernel of Aut_{±μ}(O) → N_{Bˣ}(O)/Qˣ from the `Aut` map object (`code/level-structure/aut_mu_O.m:9` returns the map; kernel elements are those whose Bˣ/Qˣ-image is trivial — but the map as constructed is claimed injective, so the correct kernel per Q2 may live elsewhere, e.g. in the semidirect product; follow the answer).
3. Fix/confirm `gerbiness`/`aut_gerbiness` in `createRecord`; if Q2 says the current numbers are right but the issue's expectation applies to a *different* column, document that in the issue-resolution note instead of changing code.
4. Add sanity assertions from Q2.4 (e.g. `deg_mu eq 1 implies <quantity> eq 1`) behind the existing test hooks; extend `tests/regression_enumerateH_small.m` with a gerbiness check for the D=6, deg 1, N=3 record against the (post-fix) known value.
5. Regenerate `data/quaternion-orders/*polarized*` (`EnumerateOmu(1000 : Write:=true)`, background — long) and, if `createRecord` changed, the `genera-D6-*` corpus (README driver loop; the D6/deg6/N6 case alone took ~33 min historically — run all 15 in background, ~1h total). Diff old vs new: only gerbiness-related columns change.
6. Stage a column update file for the DB (`label|gerbiness|aut_gerbiness` via `update_from_file`) in `artifacts/`, load commands in the Log.
7. Draft a comment for upstream issue #6 describing the resolution (do not post it — leave in Log for David).

## Acceptance criteria

- Definitions written as docstrings; both code sites derive from them.
- Sanity assertion holds over all regenerated data; tests green.
- Diff of regenerated vs old data shows changes only in the intended columns, summarized in the Log.

## Log

- 2026-07-16: ticket created from survey.
