---
id: T24
title: Frontend bug sweep (lmfdb repo, branch shimura_curves)
status: open
owner: none
priority: P1
tier: 4
repos: [lmfdb]
depends_on: []
questions: []
---

## Context

Known defects in `~/claude/lmfdb/lmfdb/shimura_curves/` (branch `shimura_curves`; **active collaborator traffic — rebase before starting and keep the change list tight**):

1. **Sage download broken**: `main.py:560` calls `download_Shimura_curve(...)`; the method is `download_shimura_curve` (`main.py:540`). `/download_to_sage/<label>` 500s. Fix + add a test hitting all three download routes.
2. **Points column mismatch**: search code uses `Elabel` (`main.py:909`), curve page uses `Clabel` (`web_curve.py:780,847-848,865-866`). Resolve to whatever `shimcurve_points` actually has (coordinate with T03; devmirror `\d shimcurve_points` is authoritative).
3. **Copied test asserts modular-curve content**: `test_shimura_curves.py:12` checks for `X_0(N)` — rewrite the test to assert real Shimura content (e.g. homepage loads, a known curve page contains its label and "Shimura").
4. **Leftover modcurve knowls/wording**: `shimcurve.html:369` (`modcurve.fiber_product` + "realize this modular curve as a fiber product"), `shimcurve.html:407` (`modcurve.modular_cover`), magma-download comment `main.py:502`. Point at `shimcurve.*` knowls (T26 creates them; referencing a not-yet-existing knowl renders as a broken-knowl link, acceptable on beta) and fix wording.
5. **Stats count workaround**: `main.py:1059-1062` counts `{'discB': {'$gt': 0}}` with comment "For some reason counting the empty query returns 0 ?" — root-cause it (likely the stats/counts table for `gps_shimura_test` is stale on the DB, `gps_shimura_test_counts` rows; check `db.gps_shimura_test.stats.total`) and either fix properly or document why the workaround stays.
6. **Dead code**: `url_for_RZB_label`/`url_for_CP_label` (`main.py:224-227`) + the `CP_LABEL_GENUS_RE` import (`main.py:56`), unused `FINE_LABEL_RE` (`main.py:61`), duplicate unused `shimcurve_link` (`main.py:120-124`, hardcodes a stray level≤70 cutoff), unused `web_curve.py` methods (`full_torsion_field_degree:573`, `newform_level:734`, `old_db_nf_points:877-895` and its `ec_nfcurves` import). Delete.
7. **Commented-out feature blocks** — do NOT delete, they're staged features: CM-points search (`main.py:293,304,615-627,798-807,860,873-874`), rational/non-rational points sections (`shimcurve.html:185-240`), low-degree-points link (`shimcurve_browse.html:49-53`), `points_type` noncm option (`main.py:607-608,818`), `factor` search box (`main.py:768-773`). Add a single `# STAGED: enable when <table/column> is populated (see shimcurve_tickets T03/T15)` marker on each so their purpose is discoverable.
8. **`contains_negative_one` vs `is_coarse`**: commented template block at `shimcurve.html:223-227` references the old column name; reconcile with T11's outcome.

## Steps

1. `git -C ~/claude/lmfdb checkout shimura_curves && git pull` (note upstream drift in the Log); branch `ticket/T24`.
2. Fix items 1-6, marker-pass item 7-8. Keep each item its own commit for reviewability.
3. Test: `cd ~/claude/lmfdb && sage -python -m pytest lmfdb/shimura_curves/ -x` plus a manual pass on a running dev server (`sage -python start-lmfdb.py --debug`): homepage, search with results, one curve page per kind (level-1, level-structure, Eichler `X(D,M;1)`), all three downloads, random, stats, diagram page.
4. List the verification evidence in the Log. Leave the branch local; David pushes/PRs.

## Acceptance criteria

- All 8 items addressed with per-item commits; pytest green; manual checklist in the Log with no 500s.

## Log

- 2026-07-16: ticket created from survey.
