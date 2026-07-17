---
id: T27
title: Rename gps_shimura_test; release checklist
status: open
owner: none
priority: P2
tier: 4
repos: [ShimCurve, lmfdb, db-readonly]
depends_on: [T02, T03, T07, T11, T14, T24, T25]
questions: [Q12]
---

## Context

The main table's `_test` name (and its 10 accumulated `_old*` snapshots on the server) signal pre-release state. Final gate: rename per Q12.3, reload clean data, flip the sidebar out of beta when ready.

## Steps

1. Inventory every reference to `gps_shimura_test`: lmfdb repo (`grep -rn gps_shimura_test ~/claude/lmfdb/lmfdb/` — main.py×8, web_curve.py, stats) and ShimCurve (guide docs, make-table). Same for any table renames from Q12.3.
2. Prepare the rename as a coordinated change: one lmfdb commit switching the table name behind a single module-level constant (introduce `SHIMCURVE_TABLE = "..."` if not already factored), one DB-side script for David (`ALTER TABLE ... RENAME` or fresh `create_table` + reload from the regenerated corpus — prefer fresh create: the accumulated `_old*` tables and stale `_counts`/`_stats` argue for a clean start; include `db.<table>.stats.refresh_stats()` and search-column/sort configuration in the script).
3. Final reload: assemble the definitive upload fileset from all landed tickets (T04-format corpus + T12/T14/T15/T17/T18 update files), load order documented; verifiers from T25 run green post-load.
4. Release checklist (execute + check off in the Log): pytest suite; T24 manual page checklist; stats page shows correct totals; downloads round-trip; jump box resolves names and fiber products; sidebar entry text/status reviewed (`~/claude/lmfdb/lmfdb/homepage/sidebar.yaml:98-101`); rcs knowls uploaded (T26); CONTRIBUTORS.yaml current.
5. Coordinate: this ticket is mostly David-executed (DB writes, knowl uploads, PR to assaferan/lmfdb or upstream LMFDB); the agent's deliverable is the scripts, the fileset, and the checklist with everything pre-verified that can be.

## Acceptance criteria

- Rename lands in one reviewable commit + one DB script; verifier suite green on the renamed, reloaded table; checklist fully executed.

## Log

- 2026-07-16: ticket created from survey.
