---
id: T14
title: Populate Jacobian columns for all rows
status: open
owner: none
priority: P1
tier: 2
repos: [ShimCurve, lmfdb, db-readonly]
depends_on: [T13]
questions: [Q13]
---

## Context

Fill, for all 2,587 rows (2,198 enhanced D=6 rows + 389 coarse rows; grows with Tier 3): `newforms, dims, mults, conductor, log_conductor, rank, simple, squarefree, genus_minus_rank, traces, trace_hash`. Currently populated only on the 339 coarse rows (plus `newforms` on 1,711). Genus-0 rows get the trivial values (empty arrays, rank 0 — copy modcurve's convention for genus 0: check `gps_gl2zhat_fine` genus-0 rows and mirror exactly).

These columns power the frontend's Jacobian section and the friends links (`web_curve.py:319-341` matches `newforms` and `trace_hash` against `lfunc_instances`).

## Steps

1. Magma pass (uses T13's `JacobianData`): iterate the regenerated data files (or a driver over the shipped (D, deg, N) parameters), compute per-H: `newforms, dims, mults, simple` (one newform, mult 1, dim = genus), `squarefree` (all mults = 1), `conductor` (per Q13.1 semantics — modcurve stores factored `[[p,e],...]`? verify with `select conductor from gps_gl2zhat_fine where genus>0 limit 3;` and copy), `traces` (a_p of Jac = Σ mults·(newform a_p sums over the orbit) — modcurve stores the first ~1000? check length convention), `genus_minus_rank` left for step 2. Write intermediate file keyed by label.
2. Python pass (`sage -python`, read-only db): for each row's newform list, pull `analytic_rank` (and `dim`) from `db.mf_newforms`; `rank = Σ mult·analytic_rank` (per Q13.1); `genus_minus_rank = genus − rank`; `log_conductor = Σ mult·log(newform conductor^dim)`? — **derive the formula from how modular curves computed it** (check `gps_gl2zhat_fine.log_conductor` vs conductor on 3 rows rather than guessing); `trace_hash` via `lmfdb.utils.trace_hash` (import `TraceHashClass`/the standard function — find it: `grep -r "trace_hash" ~/claude/lmfdb/lmfdb/utils/`) applied per modcurve convention (hash of the Jacobian's a_p sequence; confirm against one modcurve row by recomputation).
3. Missing-newform handling: if a needed CMF isn't in cmfdata/LMFDB range, leave the row's columns NULL and count it; report the count + the max level needed in the Log (drives cmfdata regeneration).
4. Cross-checks before staging: (a) recompute the 339 already-populated rows — must match exactly (any mismatch: investigate, do not overwrite silently, log it); (b) Σ dims·mults = genus for every row; (c) `simple ⟺ len(dims)==1 and mults==[1]`; (d) traces of the coarse curve X₀(6;N) match `JLDecomposition` output.
5. Stage `artifacts/T14-jacobian-update.txt` (`update_from_file` format, label-keyed) + load commands in the Log.
6. Post-load verification plan: friends links appear on a genus>0 curve page (e.g. the genus-1 curves should link to elliptic curves/CMFs via trace_hash match).

## Acceptance criteria

- All shipped rows either populated or NULL-with-reason (tallied in the Log).
- The four cross-checks pass corpus-wide; the 339-row agreement check documented.
- Staged file lints (column count, types, label regex).

## Log

- 2026-07-16: ticket created from survey.
