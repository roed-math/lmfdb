---
id: T26
title: Draft the shimcurve.* knowls
status: open
owner: none
priority: P3
tier: 4
repos: [lmfdb]
depends_on: []
questions: []
---

## Context

The templates/code reference ~50 knowls that must exist in the knowl database before release. Full list referenced by the module:

`shimcurve.{pqm, standard, level, index, genus, rank, genus_minus_rank, discb, disco, nrdmu, gonality, elliptic_points, decomposition, simple, is_coarse, models, known_points, local_obstruction, level_structure, modular_cover, relative_index, quadratic_refinements, quaternion_algebra, order, polarized_order, endomorphism_galois_group, torsion_subgroup, plane_model, embedded_model, model, invariants, cm_discriminants, isolated_point, point_degree, point_residue_field, j_invariant_map, elliptic_curve_of_point, fiber_product, rational_points, nonrational_point, label, search_input}` plus `portrait.shimcurve` and `rcs.{source,ack,cite,cande,rigor}.shimcurve`.

Knowls live in the knowl DB (edited via the website when logged in as an editor), not the repo — so this ticket produces **drafts as markdown files**, David uploads.

## Steps

1. Create `~/claude/lmfdb/shimcurve_tickets/artifacts/knowls/<knowl-id>.md`, one per knowl: title + body in knowl markdown (KaTeX math, `{{KNOWL(...)}}` cross-references). Model tone/length on the modular-curves analogues — fetch a few for calibration: `https://beta.lmfdb.org/knowledge/show/modcurve.level` etc. (if unreachable from this network, note it and work from the modcurve template usage instead).
2. Definitions must follow the enhanced-representation framework (LSSV arXiv:2308.15193 §3.5) and the QUESTIONS.md answers where they exist (gerbiness, coarse/fine, labels — leave `{{TODO}}` markers where a Q is unanswered rather than guessing).
3. The rcs.* knowls (source, reliability, completeness) should state exactly what the data is and how it was computed — pull the honest statements from BOARD.md's data-state section + Q12.4's answer.
4. `shimcurve.label` is the big one: full grammar of coarse/fine/order/mu/psl2 labels; write it as the normative spec (coordinate with T11).
5. Index file `artifacts/knowls/INDEX.md` mapping id → one-line summary → status (draft/needs-Q/final).

## Acceptance criteria

- Every referenced knowl id has a draft file; unanswered-question gaps are explicit TODO markers, not invented math; INDEX.md complete.

## Log

- 2026-07-16: ticket created from survey.
