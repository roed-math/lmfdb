---
id: T06
title: quaternion-orders data hygiene (header, area convention, disc semantics, row drift)
status: open
owner: none
priority: P1
tier: 0
repos: [ShimCurve, db-readonly]
depends_on: []
questions: [Q3, Q14]
---

## Context

Four defects in the `quaternion_orders` / `quaternion_orders_polarized` generation (`code/quaternion_orders/enumerate-O.m`):

1. **Header/row mismatch**: `EnumerateO`'s `.m` writer emits a 7-column header (`:126-127`) but `LMFDBRowEntry(O)` (`:47`) emits 9 fields (adds `area_numerator`, `area_denominator`). File: `data/quaternion-orders/quaternion-orders.m`. The `.txt` variant (`:155`) is consistent (9/9).
2. **Area value discrepancy**: same order (D=6 maximal) has area 1/6 in the `.txt` and 1/3 in the `.m` — a factor-2 convention drift somewhere in history. `Area(O)` (`:34`) currently computes φ(D)ψ(M)/12. → Q14 decides the intended normalization; then regenerate whichever file is wrong.
3. **Column semantics inverted**: in `quaternion-orders.txt` the column headed `discO` holds the **algebra** discriminant D and `discB` holds the order's reduced discriminant D·M — backwards relative to every other use (`gps_shimura_test` has discB = algebra, discO = order) and to the label convention documented in `data/quaternion-orders/make-table.m`. Check whether the devmirror `quaternion_orders` table (columns `discO, discB`) inherited the inversion: `select label,"discO","discB" from quaternion_orders where label='6.30';` — for the Eichler order 6.30, algebra disc is 6 and order disc is 30; record which column holds which.
4. **Row drift**: `quaternion-orders-polarized.m` has 800 rows vs `quaternion-maximal-orders-polarized.txt` 804 (devmirror table: 890 incl. 86 Eichler rows). Diff the label sets, find the 4 missing/extra rows, and determine the cause (resume logic in `EnumerateOmuTxt` `:328-437` vs the plain writer; nondeterminism from `Embed` — cf. Q3/T08).

## Steps

1. Fix the `.m` header to 9 columns matching `LMFDBRowEntry`.
2. Resolve Q14 → fix `Area` or the stale file; add a one-line comment stating the convention with the formula.
3. Fix the `discO`/`discB` inversion at the source (writer column order or the header naming — pick whichever makes files, DB, and `make-table.m` agree; the DB is live so if the DB itself is inverted, note that a column-content swap must ship with the next reload and flag it prominently in the Log for T27).
4. Diff the 800-vs-804 label sets; explain each difference in the Log; make the two writers produce identical row sets for the maximal range.
5. Regenerate all four files with a bounded run (`EnumerateO(1000 : Write:=true)`, `EnumerateOmu(1000 : Write:=true)` — README timings suggest minutes-to-hours; run in background and note wall time), then re-diff against the old files: only the intended fields change.
6. `tests/run_quick.m` green; stage load commands in the Log (tables reload via `copy_from` after truncate — spell out exactly, David executes).

## Acceptance criteria

- All four defects fixed at the source and demonstrated by regenerated files + diffs in the Log.
- A grep for `discO`/`discB` across ShimCurve writer code shows consistent semantics (algebra=discB, order=discO) — or the deliberate opposite, documented once.

## Log

- 2026-07-16: ticket created from survey.
