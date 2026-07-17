---
id: T02
title: Relabel + stage the models upload; create shimcurve_modelmaps / shimcurve_teximages tables
status: open
owner: none
priority: P0
tier: 0
repos: [ShimCurve, lmfdb, db-readonly]
depends_on: [T01]
questions: [Q1]
---

## Context

The frontend renders models and maps between models, reading three tables:

- `db.shimcurve_models` — exists on devmirror with **1 row**. Columns (from frontend usage, `~/claude/lmfdb/lmfdb/shimura_curves/web_curve.py:411,420,544-547`, `main.py:424-426,469-471`): `shimcurve` (curve label FK), `equation`, `number_variables`, `model_type`, `smooth`, `dont_display` (+ comment mentions `gonality_bounds`).
- `db.shimcurve_modelmaps` — **does not exist**. Frontend expects `domain_label, domain_model_type, codomain_label, codomain_model_type, coordinates, leading_coefficients, factored, degree, dont_display` (`web_curve.py:430-435,567`, `main.py:464-467`).
- `db.shimcurve_teximages` — **does not exist**. Frontend expects `label, image` (`web_curve.py:1011`); for modular curves this holds pre-rendered TeX images of level-structure names used in lattice diagrams.

Local data: `~/claude/ShimCurve/data/models/lmfdb_shim_models.txt` (462 records, old labels, no header). Record shape appears to be `f|{equation}|[opt int]|int|int|old_label|t` — the field roles must be pinned down against the modular-curve analogue and the 1 existing devmirror row.

`model_type` codes in the frontend (`web_curve.py:441-470`): 0 = canonical, 2 = plane, 5 = Weierstrass?, 7 = geometric hyperelliptic, 8 = embedded (check the code — the mapping is explicit there).

## Task

Produce postgres-ready upload files for `shimcurve_models` under the **new** labels, plus `create_table` statements for `shimcurve_modelmaps` and `shimcurve_teximages`, and exact load commands. Do **not** run anything against a writable database.

## Steps

1. Inspect the existing devmirror row and the modular-curve templates:
   `select * from shimcurve_models;` and `\d modcurve_models`, `\d modcurve_modelmaps`, `\d modcurve_teximages` — use the modcurve schemas as the blueprint (drop columns Shimura can't fill yet rather than inventing new ones).
2. Parse `lmfdb_shim_models.txt` handling multi-line equations (a new record starts on a line whose first field is `t`/`f` — verify). Establish each positional field's meaning by cross-checking: the `number_variables` int must equal the number of distinct variables in the equation; `model_type` must be consistent with equation shape (conic/quartic in 3 vars ⇒ plane=2; y² = sextic ⇒ geometric hyperelliptic).
3. Apply T01's label map (`artifacts/T01-label-map.csv`). Rows mapping to UNMAPPED go to a parked file `artifacts/T02-models-parked.txt` with the same format (they wait on Q1.2 / T19-T21 coverage).
4. Emit `artifacts/T02-shimcurve_models.txt` in standard copy format (3 header lines: names, types, blank), matching the devmirror table's columns exactly; set `dont_display = f` except where the source marked otherwise.
5. Write the `create_table` calls for `shimcurve_modelmaps` and `shimcurve_teximages` (mirroring modcurve types), and — if any model maps are derivable from the source data (they may not be) — an upload file for them too.
6. Also stage the update of `gps_shimura_test.models` (smallint: number of displayed models per curve) for affected labels: emit `artifacts/T02-gps-models-count-update.txt` with columns `label|models` suitable for `db.gps_shimura_test.update_from_file`.
7. Append to this ticket's Log the exact commands for David to run, e.g.:
   ```python
   # sage -python, editor credentials, from ~/claude/lmfdb
   from lmfdb import db
   db.shimcurve_models.copy_from('.../T02-shimcurve_models.txt', sep='|')
   db.create_table(...)  # modelmaps, teximages — spelled out fully in the Log
   ```
8. Verification: reload a local LMFDB dev server pointed at a database where David has loaded the file (or, before that, unit-test the parse by round-tripping 5 sample records) and confirm the Models section renders on one affected curve page.

## Acceptance criteria

- Upload file passes a lint script (correct column count on every record, all labels match `LABEL_RE` from `main.py:60`, equations non-empty, types line matches the table).
- Parked file + upload file together account for all 462 source records.
- `create_table` statements are complete (search columns, label column, sort order specified) and copied into the Log.

## Log

- 2026-07-16: ticket created from survey.
