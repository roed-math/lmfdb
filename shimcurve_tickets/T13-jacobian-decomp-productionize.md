---
id: T13
title: Make jacobian_decomp production-ready + acquire cmfdata
status: open
owner: none
priority: P1
tier: 2
repos: [ShimCurve, db-readonly]
depends_on: []
questions: [Q13]
---

## Context

`code/jacobian_decomp/` computes isogeny decompositions of Jac(X_H) by Jacquet–Langlands + trace matching:

- `helpers.m` — `CMFLoad` reads an external **`cmfdata.txt`** (`:66`; record format `cmfrec` at `:13-19`) which is **not in the repo**; `ClassNumberTable` caches to `xgclassnumbers.dat` (also absent, but auto-generated).
- `indefinite.m` — trace formula (`IndefiniteTrace`) + `HTraces(H,...)` (Frobenius traces of X_H over F_q).
- `level_dividing_D.m` — local GL₂(O_p) models for p | gcd(D, N·M) (`BuildG`, `BuildGSubgroup`, `FindI/FindJ/Findc` with retry-style string errors "increase NumTries"/"increase Bound or NumTries").
- `newform_decomp.m` — `JLDecomposition` (for J₀^D(N)) and `ShimuraNewformDecomposition(H,...)` (general X_H): solves a linear system matching H-traces against newform traces; failure codes −1 (genus 0), −2 (linear-system), −3 (cutoff) documented at `:62`; stray debug `print` at `:74, :83-86`.

This is the machinery for the currently-null columns `newforms, dims, mults, conductor, rank, simple, squarefree, genus_minus_rank, traces, trace_hash` (T14 does the mass computation; this ticket makes the tool trustworthy). The 339 rows that already have decomposition data came from the X₀(D;N) arm (`tablesX0DN.m:1` "requires downloading the appropriate cmf data") — the same cmfdata dependency.

## Steps

1. **cmfdata.txt**: reverse-engineer the exact format from `CMFLoad`/`cmfrec` (fields, separators, sort). Write `code/jacobian_decomp/make_cmfdata.py` (sage -python) that dumps it from the LMFDB: `db.mf_newforms` (+ `db.mf_hecke_traces` or the `traces` column) restricted to weight 2, trivial character, level ≤ a parameter; include whatever `cmfrec` needs (per Q13.2 — likely label, level, dim, traces list, AL eigenvalues from `fricke_eigenval`/`atkin_lehner_eigenvals`). Document the command and generate a file covering level ≤ 4000 (enough for D·N·M in current scope) into `~/claude/ShimCurve/data/cmfdata/` (gitignored if large; note size).
2. Remove debug prints; convert string/int error returns into Magma errors or `<ok, result, reason>` returns consistently; make the retry parameters (`NumTries`, `Bound`) self-escalating with a hard cap instead of asking the caller to retry.
3. Determinism/robustness pass on `ShimuraNewformDecomposition`: the linear system must be checked for unique solvability (currently what happens on underdetermined systems? −2?); raise the trace cutoff adaptively until the solution is unique or the cap hits; assert Σ dims·mults = genus at the end (fundamental consistency check).
4. Validate against ground truth: the 339 devmirror rows with `dims/mults/newforms` populated (X₀(D;N) rows). Recompute ≥ 20 of them across different D (query: `select label,"discB","discO",newforms,dims,mults from gps_shimura_test where dims is not null limit 20;`) and require exact agreement. Also validate `JLDecomposition` for 2-3 classical cases from the literature (e.g. J₀^6(1) trivial, a known D=6 N=5 or D=10 decomposition).
5. Wire a convenience intrinsic `JacobianData(H, G, O, mu, N) -> rec` returning all columns T14 needs (newforms sorted by `CMFLabelCompare`, dims, mults, conductor = product/factored per Q13.1, simple, squarefree), leaving rank/trace_hash to T14 (they need LMFDB analytic-rank data / the hash algorithm, python-side).
6. Add `tests/regression_jacobian_decomp.m` (one small X_H with known decomposition; keep < 2 min).

## Acceptance criteria

- `make_cmfdata.py` reproducibly generates the file; format documented in the script header.
- 20-row ground-truth validation passes; Σ dims·mults = genus asserted globally.
- No debug prints; failure modes are structured; regression test green.

## Log

- 2026-07-16: ticket created from survey.
