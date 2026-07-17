---
id: T05
title: Fix or remove stale readers; update README data section and roundtrip test
status: open
owner: none
priority: P1
tier: 0
repos: [ShimCurve]
depends_on: [T04]
questions: []
---

## Context

Three things still speak the **legacy** `EnumerateH` output format (9 columns, `QuaternionAlgebra<...>` preamble, rows containing `<...>` tuples), which the current pipeline no longer writes:

1. `code/utils/read-write.m` — `LineToRecord` (`:2`) and `GeneraTableToRecords` (`:41`) only accept lines containing `<`; on current 68/70-column files they silently skip **every** data row.
2. `code/upload_scripts/shimcurve_generate.py` — parses the legacy preamble (`:26-57`), plus two open TODOs (`:19` coarse/fine, `:22` ram_data_elts). The current files are direct `copy_from`-ready, so this script's role is gone.
3. `README.md` "## Data" section (~lines 246-270) — documents the legacy format, contradicting the "# Data for LMFDB" section above it.

Also `tests/data_roundtrip.m` writes a synthetic **legacy** fixture and tests the legacy reader — it passes while testing the wrong thing.

Downstream consumers of `GeneraTableToRecords` exist (`qm-mazur/ICERM-code-demo.m:2`, `qm-mazur/utils-qm-mazur.m` `read_data`) — the Magma reader is genuinely useful for research scripts and should be **fixed, not deleted**.

## Steps

1. Rewrite `GeneraTableToRecords`/`LineToRecord` to parse the canonical format from T04: read the 3-line header, map column names → record fields, split rows on the canonical separator, decode `{...}` sequences / `T`/`F` / `\N`, and decode `generators` (8·k integer lists → pairs of O-elements) and `ram_data_elts` (Lehmer ranks via `DecodePerm`, `code/level-structure/lehmer.m:8`). Return records compatible with what `ICERM-code-demo.m` expects (check its usage and adapt either side).
2. Rewrite `tests/data_roundtrip.m`: generate a tiny real dataset (D=6, deg 1, N=1 → 5 rows) via the actual writer into a temp path, read it back with the new reader, assert genus/index/torsion of a known row (`X(6;1)`: genus 0, fuchsian_index 1 — verify against `data/genera-tables/genera-D6-deg1-N1.m` before hardcoding). Keep it deterministic and under ~2 min.
3. Delete `code/upload_scripts/shimcurve_generate.py` (git preserves it) and replace with `code/upload_scripts/README.md` documenting the actual load path:
   ```python
   from lmfdb import db
   db.gps_shimura_test.update_from_file('data/genera-tables/<file>', sep='?')   # or copy_from for fresh tables
   ```
   copying the fuller recipe from `code/utils/lmfdb-data-guide.txt:36-80` and `data/quaternion-orders/make-table.m`.
4. Rewrite README "## Data" to describe the current 70-column format (reference the T04 schema constant), and remove the legacy example.
5. `tests/run_quick.m` green.

## Acceptance criteria

- `GeneraTableToRecords` on `data/genera-tables/genera-D6-deg1-N2.m` returns 28 records with correct genus values (spot-check 2 against the file).
- `qm-mazur/ICERM-code-demo.m`'s read step works (run just its first lines) or its call site is updated in the same commit.
- No code in the repo parses the legacy format; README sections agree with each other.

## Log

- 2026-07-16: ticket created from survey.
