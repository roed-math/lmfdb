---
id: T25
title: verify/ schema checks + table specification docs
status: open
owner: none
priority: P2
tier: 4
repos: [lmfdb, ShimCurve, db-readonly]
depends_on: [T04]
questions: []
---

## Context

LMFDB tables ship with consistency checks under `~/claude/lmfdb/lmfdb/verify/` (e.g. `verify/modcurve/modcurve_modelmaps.py`). Nothing exists for the Shimura tables, and there is no committed schema spec beyond the partial notes in `~/claude/ShimCurve/code/utils/lmfdb-data-guide.txt` and `data/quaternion-orders/make-table.m`.

## Steps

1. Write `lmfdb/verify/shimcurve/` verification classes for `gps_shimura_test` (post-T27 name), `quaternion_orders`, `quaternion_orders_polarized`, `shimcurve_models`, `shimcurve_points`. Crib structure from `verify/modcurve/`. Checks worth encoding (each is a real invariant from the pipeline):
   - label ↔ (discO, deg_mu, level, index, genus, class, num) consistency; coarse_label consistency; mu_label = order_label.deg_mu; order_label exists in quaternion_orders; mu_label exists in quaternion_orders_polarized.
   - genus from Riemann–Hurwitz data: 2·index·(χ-ish via area) consistency — encode the Gauss–Bonnet identity used at `enumerate-H.m:280-283`: fuchsian_index, ν-counts, genus satisfy Area·index = 2g−2 + Σ ν_e(1−1/e).
   - Σ dims·mults = genus where dims present; simple/squarefree consistency with dims/mults; genus_minus_rank = genus − rank.
   - q_gonality within q_gonality_bounds; qbar ≤ q; bounds ordered.
   - parents: every parent label exists; parent index divides; parent genus ≤ genus.
   - pointless ⟹ num_known_degree1_points = 0; cm_discriminants are valid imaginary quadratic discriminants.
   - level_is_* flags match level; bad_primes = prime divisors of discO·level.
2. Table specs: write `~/claude/ShimCurve/code/utils/table-schemas.md` documenting every column of every table (name, type, definition, provenance ticket) — generated partly from T04's canonical constant; this becomes the reference the (future) preprint and knowls cite.
3. Run the verifiers against devmirror data; every failure is either a data bug (file a Log note + ticket reference) or a wrong check (fix). Expect hits: the columns entirely NULL are fine (verify skips), but e.g. the Gauss–Bonnet check will exercise the coarse rows' ν-columns immediately.
4. Keep the verify code on a local lmfdb branch `ticket/T25` for David to push.

## Acceptance criteria

- Verifier suite runs end-to-end against devmirror; results table (pass/fail per check) in the Log; every failure triaged.
- `table-schemas.md` covers all columns of all 5+ tables.

## Log

- 2026-07-16: ticket created from survey.
