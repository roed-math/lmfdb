---
id: T11
title: −1 detection, is_coarse, fine labels, scalar_label
status: open
owner: none
priority: P1
tier: 1
repos: [ShimCurve, lmfdb]
depends_on: []
questions: [Q5, Q6]
---

## Context

Label/moduli bookkeeping that is currently stubbed:

- `is_coarse` is hardcoded `true` for every row (`enumerate-H.m:272`); the old upload script's TODO (`upload_scripts/shimcurve_generate.py:19`) says the missing piece is "a way to tell if −1 is in the group".
- `fine_label` is set equal to the coarse-style label, `fine_num` is `\N`; the frontend already supports hyphenated fine labels (`~/claude/lmfdb/lmfdb/shimura_curves/main.py:59` FINE regex, `web_curve.py:285-287` merges coarse data into fine pages).
- `scalar_label` ends in a hardcoded `.1` with the comment "we are not sure how to label the scalar subgroup" (`enumerate-H.m:385-386`).

Q5 decides the criterion ((1,−1) ∈ H?), whether gerbiest H are automatically coarse (KG ∋ −1 would imply the current hardcode is *accidentally right* for all shipped rows), and the fine-label grammar. Q6 decides scalar_label.

## Steps

1. **Independent of Q5**: implement `ContainsMinusOne(H)` — test whether the GL₄-image of (1, −1 mod N) lies in H (the element is `EnhancedElementInGL4modN(<identity Aut elt, OmodN!(-1)>, N)`; build it via the enhanced constructors, `code/level-structure/enhanced-constructors.m` / `embed-in-GL4.m`). Compute it for every H in the shipped D=6 enumeration and record the tally in the Log — this is also the empirical answer to Q5.2.
2. Once Q5 confirms the criterion: wire `is_coarse := ContainsMinusOne(H)` (or per answer) into `createRecord`; implement fine-label assignment in `updateLabels` (`enumerate-H.m:288`) per the grammar in Q5.3, including `fine_num`.
3. Once Q6 answers: fix `scalar_label` construction (`:380-387`).
4. Frontend check (lmfdb repo): with a fine row present in a test file, confirm `combined_data` (`web_curve.py:281-290`) resolves it — the coarse-label reconstruction `mu_label + "." + coarse_label` must match the new grammar; adjust if Q5.3 differs.
5. Regenerate the D=6 corpus if any shipped column changes (likely only if some gerbiest H turn out fine — per step 1 tally). Stage update files + commands in the Log.

## Acceptance criteria

- `ContainsMinusOne` implemented + tested (add to `tests/smoke_intrinsics.m`: the full group G contains it; a constructed index-2 subgroup missing it returns false).
- Step-1 tally in the Log (and echoed under Q5 in QUESTIONS.md).
- After Q5/Q6: labels regenerate deterministically; frontend resolves both label kinds on a local check.

## Log

- 2026-07-16: ticket created from survey.
