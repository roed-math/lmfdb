---
id: T09
title: Fix Aut_{±μ}(O) construction for C4/C6/D4/D6 (aut_mu_O.m FIXMEs)
status: open
owner: none
priority: P0
tier: 1
repos: [ShimCurve]
depends_on: []
questions: []
---

## Context

`code/level-structure/aut_mu_O.m` builds Aut_{±μ}(O) as a map from an abstract group (C_n or D_n) into Bˣ/Qˣ. Two FIXMEs mark broken cases:

- `:45` — `Dn<w_chi,w_mu>:=DihedralGroup(GrpPC, cyc_order); // FIXME: there will be another generator for D4 and D6 since magma uses prime relative orders`. For cyc_order ∈ {4,6}, Magma's pc-presentation of D_n has 3 generators with prime relative orders, so `Dn.2` does **not** have order cyc_order; the adjacent `assert Order(Dn.2) eq #Dn/2` and the element-list construction `[ <Dn.1^k*Dn.2^l, ...> ]` enumerate the wrong elements.
- `:57` — `Cn<w_mu>:=CyclicGroup(GrpPC, cyc_order); // FIXME: this will be a problem for C4 and C6` — same issue for the cyclic case (`Cn.1` has prime order in the pc-presentation for composite n).

These cases arise exactly when μ generates a cyclotomic quadratic order (the code detects sqeta = −1 → order 4, sqeta = −3 → order 6 just above, `:20-40`), so any (O, μ) whose automorphism group is C4/C6/D4/D6 currently gets a wrong `Aut` map — poisoning `AutmuO_size`, `AutmuO_label`, `AutmuO_generators`, `AutmuO_is_cyclic` in `quaternion_orders_polarized` and everything downstream in the enhanced enumeration for those μ.

The final `assert MapIsHomomorphism(grp_map : injective:=true)` (`:65`) may or may not catch the breakage (it checks the constructed element list, which could be silently wrong-but-consistent) — determine which.

## Steps

1. Build failing examples: search `quaternion_orders_polarized` (devmirror) for rows with `AutmuO_label` in ('C4','C6','D4','D6') to find concrete (O, μ); if none exist (possible — the bug may have prevented generation), construct one directly: need μ with μ²= −disc·d and a twisting pair giving the cyclotomic case; D=10 or D=15 with small degrees are natural hunting grounds; also grep `data/quaternion-orders/*polarized*` for those labels.
2. Reproduce the failure (or demonstrate silent wrongness) in a Magma session; record it in the Log.
3. Fix: use `GrpPC` presentations correctly (address elements via `Dn ! [exponent vector]` or construct via `PolycyclicGroup< a,b | a^2, b^n, b^a = b^-1 >`), or switch to `GrpPerm`/`GrpFP` (`DihedralGroup(GrpPerm, n)` has 2 generators with the expected orders — check what downstream code needs; `Domain(AutmuO)` is used for `GroupName`, `IsCyclic`, generator indexing `.1`/`.2` in `enumerate-O.m:270-273`, and as the domain of `Ahom` in `embed-in-GL4.m:373`).
4. Make the element-list construction independent of generator conventions: build `elts` by iterating over the group's elements with a well-defined decomposition rather than exponent pairs `(k,l)`.
5. Strengthen the homomorphism test to also assert `#image eq #Domain` and that orders match (`Order(g) eq Order(image under map)` for generators).
6. Add a regression test to `tests/` exercising one C4-or-C6 and one D4-or-D6 example end-to-end (`Aut` + `EnhancedImageGL4` at small N).
7. If any shipped `quaternion_orders_polarized` rows carried wrong Aut data, list the affected labels in the Log and stage corrected rows (coordinate with T06/T08 regeneration — if those run after this fix, no separate staging needed).

## Acceptance criteria

- A previously-failing (or silently wrong) example now produces a verified homomorphism with the right group; regression test in `tests/` covers it.
- `run_quick.m` green; affected-rows analysis in the Log.

## Log

- 2026-07-16: ticket created from survey.
