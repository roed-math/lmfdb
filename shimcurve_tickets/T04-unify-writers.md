---
id: T04
title: Unify the two table writers on one canonical schema
status: open
owner: none
priority: P0
tier: 0
repos: [ShimCurve]
depends_on: []
questions: []
---

## Context

Two writers emit rows for the same postgres table (`gps_shimura_test`) with **incompatible layouts**:

- `WriteHeaderAndSubgroupsDataToFile` / `WriteHeaderToFile` / `WriteSubgroupsDataToFile` (`code/level-structure/enumerate-H.m:498-618`; canonical list `GPS_SHIMURA_FIELDS` at `:427-496`): **68 columns**, `?`-separated. Asserts 68 fields per row (`:614`).
- `X0DNdata` (`code/tables/tablesX0DN.m:30-31`): **70 columns**, `|`-separated — adds `level_is_prime`, `level_is_prime_power`, and places `aut_gerbiness` at a different position.

The devmirror table has all 70 columns, so the canonical schema is the 70-column superset. Keeping two hand-maintained column lists is how the mismatch happened; they were merged into the DB manually.

## Task

Single source of truth for the schema; both writers emit identical headers and compatible rows.

## Steps

1. Create one Magma constant (e.g. `GPS_SHIMURA_FIELDS` moved to `code/utils/schema.m`, added to `spec`) holding the ordered 70 `<name, postgres-type>` pairs — order matching the current devmirror `gps_shimura_test` column order (pull with `\d gps_shimura_test`; exclude `id`).
2. Make `WriteHeaderToFile`/`WriteSubgroupsDataToFile` consume it: add the two missing columns (`level_is_prime := IsPrime(level)`, `level_is_prime_power := IsPrimePower(level)` — match how `tablesX0DN.m` computes them, note level 1 edge case) and replace the `assert nf eq 68` with the list length.
3. Make `tablesX0DN.m` consume the same constant. Decide one separator for both (recommend `|`, since `?` appears inside no field but `|` matches the larger existing corpus — actually **check both corpora for separator collisions first** and record the finding in the Log; psycodict `copy_from` accepts any sep).
4. Keep a regeneration escape hatch: writers should take the field list from the constant so future column additions happen in exactly one place. Add a comment in the constant pointing at `lmfdb-data-guide.txt` and this ticket.
5. Regenerate one small file of each kind and diff against the old ones column-by-column (`genera-D6-deg1-N1.m` — 5 rows, fast: the README driver with `deg=1, N=1`; and a tiny X0DN run, e.g. `X0DNdata(30, 1)` variant) to prove only the intended layout changed, not values. **Do not regenerate the full corpus in this ticket** (Tier-1 fixes will force regeneration anyway).
6. Run `tests/run_quick.m`; update `tests/data_roundtrip.m` expectations if the header layout is what it checks (see T05 — coordinate if both in flight).

## Acceptance criteria

- Exactly one ordered column list exists in the codebase; both writers reference it.
- Sample regenerated files: identical values to the old files modulo the two added columns and separator; documented diff in the Log.
- `tests/run_quick.m` passes.

## Key files

- `code/level-structure/enumerate-H.m:427-496` (field list), `:498-618` (writers)
- `code/tables/tablesX0DN.m:30-31` (header), `:110-112` (driver caps)
- `code/utils/lmfdb-data-guide.txt` (upload recipe to keep in sync)

## Log

- 2026-07-16: ticket created from survey.
