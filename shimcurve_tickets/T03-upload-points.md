---
id: T03
title: Relabel + stage the rational-points upload (shimcurve_points)
status: open
owner: none
priority: P0
tier: 0
repos: [ShimCurve, lmfdb, db-readonly]
depends_on: [T01]
questions: [Q1]
---

## Context

`db.shimcurve_points` exists on devmirror with **0 rows**. The frontend's point search and curve-page point tables read: `curve_label, curve_name, curve_genus, curve_level, curve_index, degree, isolated, cm, residue_field, j_field, jinv, jorig, j_height, coordinates, cusp, conductor_norm` and an elliptic-curve label column (`~/claude/lmfdb/lmfdb/shimura_curves/main.py:900-914`, `web_curve.py:765-781`). Note a known frontend inconsistency: search code uses `Elabel`, curve pages use `Clabel` (T24 fixes this — coordinate on which name the table will use; check the actual devmirror schema with `\d shimcurve_points` and treat it as authoritative).

Local data: `~/claude/ShimCurve/data/rational points/lmfdb_shim_rational_pt_updated.txt` — ~424 records, 20 pipe-delimited columns, no header. Populated: col 3 = number of rational points (`0`…`10`, `infinite`), col 6 = coordinate list `{[4,-9,1],...}` or `[]`, col 7 = 0/1, col 11 = `1`, col 12 = old curve label. Everything else `\N`.

Important: this file mixes two kinds of information — (a) individual point records (coordinates) that belong in `shimcurve_points`, and (b) per-curve counts (`num_known_degree1_points`, `pointless`, and "infinite" ⇒ genus 0 with a rational point) that belong in `gps_shimura_test` columns.

## Steps

1. `\d shimcurve_points` on devmirror; also `\d modcurve_points` as the semantic reference. Pin down each of the 20 source columns by comparing several records against curves whose points are known (e.g. genus-0 conics with obvious points); document the inferred layout in the Log.
2. Apply T01's label map; park UNMAPPED records in `artifacts/T03-points-parked.txt`.
3. Emit two staged files in `artifacts/`:
   - `T03-shimcurve_points.txt` — one row per known point (coordinates from col 6), with `degree=1`, `residue_field='1.1.1.1'`-style rationals convention copied from modcurve_points, `coordinates` in the model/coordinate convention the frontend displays (check `web_curve.py` display code; coordinates must reference a model uploaded in T02 — if the model reference scheme is per `model_type`, encode which model the coordinates live on).
   - `T03-gps-points-update.txt` — per-curve update file (`label|num_known_degree1_points|pointless|...`) for `db.gps_shimura_test.update_from_file`: count `0` ⇒ `num_known_degree1_points=0` (leave `pointless` NULL unless a proof exists — a search finding nothing is not pointlessness), `infinite` ⇒ set `num_known_degree1_points` NULL? or a sentinel — **check how modular curves handle genus-0 infinite points** (they use `pointless=f` and leave counts for isolated points; copy that convention) — document the decision.
4. Write load commands into the Log (copy_from / update_from_file), for David to execute.
5. After David loads: verify one curve page shows its points, and the low-degree point search returns rows (`/ShimuraCurve/Q/low_degree_points`). Note: the curve-page points sections are currently commented out in `shimcurve.html:185-240` — re-enabling them is part of T24; verification before that lands can use the search page only.

## Acceptance criteria

- Every source record is either in a staged file or parked with a reason; a lint script validates column counts/label regex/types.
- The count-vs-point-record split is documented and consistent with modcurve conventions.
- Load commands in the Log.

## Log

- 2026-07-16: ticket created from survey.
