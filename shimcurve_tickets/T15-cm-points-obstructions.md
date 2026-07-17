---
id: T15
title: CM points, obstructions, and point counts for coarse rows
status: open
owner: none
priority: P1
tier: 2
repos: [ShimCurve, db-readonly]
depends_on: []
questions: [Q9]
---

## Context

Null columns with existing, polished machinery in `code/X0DN/X0DN_code.m` (Arango-Pineros–Padurariu–Saia; Ogg/González–Rotger-based):

- `cm_discriminants` (frontend: `web_curve.py:401-402,913`) — from `CMPointsX0DN` / `QuadraticCMPointsX0DN`.
- `obstructions`, `has_obstruction`, `pointless` — real place: Shimura's theorem (X₀(D;N)(ℝ) = ∅ for D > 1) applies to every curve admitting a map to the coarse X₀(D;N) — per Q9.3, decide the exact H-criterion for when that argument applies to X_H (Aut-projection trivial ⟹ X_H covers X₀(D;N)-mod-nothing); p-adic: Ogg/Jordan–Livné criteria at p | D per Q9.2.
- `num_known_degree1_points`, `num_known_degree1_noncm_points` — rational CM points on AL quotients from `RationalCMPointsX0DN` / `RationalCMQuotientsX0DN` give known-point lower bounds; `pointless=true` rows get 0s.
- `all_degree1_points_known` — currently hardcoded `F` for all; genuinely-true cases (pointless curves! and genus-0 curves with a point) should flip to `T` per Q9.

Scope note: start with the 389 coarse X₀(D;N)-type rows plus the D=6 level-1 quotient rows where the AL-quotient interpretation is exact; the general-X_H story (level > 1) needs the Q9.3 criterion and possibly more theory — split it out if it balloons.

## Steps

1. Read Q9. Confirm conventions against modular curves (`obstructions`: 0 = real place; `has_obstruction` smallint semantics — check modcurve: 1 = yes, 0 = none known, −1 = ?; copy exactly: `select distinct has_obstruction from gps_gl2zhat_fine;` + grep its frontend for display logic).
2. Implement `intrinsic X0DNPointsData(D, N, W) -> rec` wrapping the X0DN_code intrinsics: CM points by discriminant, rational points/quotient results, real-point status (for the quotient X₀(D;N)/W, real points can exist — use the criteria from the literature per Q9.2; Ogg's real-points criterion for AL quotients is classical), local obstructions at p | D·N.
3. Map results onto rows: coarse rows (trivial W) and the 5 D=6 level-1 rows (W from `autmuO_norms`). Emit `artifacts/T15-points-update.txt` (label-keyed update file: `cm_discriminants|obstructions|has_obstruction|pointless|num_known_degree1_points|num_known_degree1_noncm_points|all_degree1_points_known`).
4. Consistency guards: `pointless=T ⟹ num_known_degree1_points=0 and has_obstruction=1`; genus 0 + known point ⟹ infinitely many (follow modcurve's encoding for that, cf. T03); a curve with a rational CM point must have `pointless=F` and the CM disc in `cm_discriminants`.
5. Cross-validate against T03's data where they overlap (a curve with uploaded rational points must not be marked pointless — run the join and log it).
6. Stage load commands in the Log.

## Acceptance criteria

- Update file covers all targeted rows; guards pass; overlap check vs T03 clean.
- Convention table (ours vs modcurve) documented in the Log.

## Log

- 2026-07-16: ticket created from survey.
