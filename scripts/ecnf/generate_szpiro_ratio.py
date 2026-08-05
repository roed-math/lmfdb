# -*- coding: utf-8 -*-
r"""Generate the szpiro_ratio column for the ec_nfcurves table (issue #6292).

The Szpiro ratio of an elliptic curve `E` over a number field `K` is

    sigma = log(Norm(D_min)) / log(Norm(N)),

where `D_min` is the minimal discriminant ideal and `N` the conductor of
`E` (Hindry, "Why is it difficult to compute the Mordell-Weil group?",
top of p.8).  Both norms are determined by columns already stored in
ec_nfcurves:

- ``conductor_norm`` is Norm(N);
- ``normdisc`` is the norm of the discriminant of the *stored model*,
  which may be negative (it is the norm of the discriminant as a field
  element) and may fail to be minimal at the (at most one) prime listed
  in ``non_min_p``; at such a prime the stored valuation of the model
  discriminant exceeds that of the minimal discriminant by 12;
- ``local_data[i]['ord_disc']`` is the valuation of the *minimal*
  discriminant at the i-th bad (or non-minimal) prime, whose norm is
  ``local_data[i]['normp']``.

So Norm(D_min) = prod(normp^ord_disc) = |normdisc| / prod(normp^12 over
non_min_p).  Curves with everywhere good reduction (conductor_norm = 1)
have D_min = (1) as well, so sigma is not defined (0/0) and we store NULL.

For efficiency the script streams a light projection for curves whose
stored model is globally minimal (the vast majority) and only fetches
``local_data`` for the non-minimal rows; for the latter both formulas
above are computed and checked against each other.  Exactly
``--sample-check`` minimal rows are cross-checked against local_data too.

This is a one-time production migration, so the script fails closed:
every integrity problem raises (with the offending label) and exits
nonzero, and no partial file is ever left where it could be uploaded.
Rows are streamed into a temporary file next to the requested output
path, which replaces it only after both partitions have finished, all
cross-checks have passed, the row counts match, and any requested
``--verify`` recomputation has succeeded; on failure the temporary file
is removed and a pre-existing output file is left untouched.

Run from the top-level lmfdb directory (requires a working config.ini;
read access is enough):

    sage -python scripts/ecnf/generate_szpiro_ratio.py ec_nfcurves_szpiro.txt

Optional flags: ``--limit N`` (process at most N rows of each of the two
partitions: sample run), ``--sample-check N`` (number of minimal-model
rows to cross-check against local_data, default 1000, capped at the
number actually processed), ``--verify N`` (recompute N random rows of
the generated file from scratch with Sage from the a-invariants; slow
but fully independent), ``--seed N`` (reproducible sampling).

Deployment
==========

All website uses of the column are guarded by

    HAVE_SZPIRO_RATIO = "szpiro_ratio" in db.ec_nfcurves.search_cols

in lmfdb/ecnf/main.py.  That flag, the result columns, the search array
and the sort choices are all built once when the module is imported, so
adding the column does **not** activate the feature in a running web
worker, and neither does ``db.refresh_tables()``: the workers have to be
restarted.  Carry out the migration in this order.

1. Generate and verify the data file (this script)::

       sage -python scripts/ecnf/generate_szpiro_ratio.py ec_nfcurves_szpiro.txt --verify 25

2. Create the ``ec.szpiro_ratio`` knowl (web UI), so the label on the
   curve page is live as soon as the feature appears.

3. Add the column (needs an account with write access; not possible on
   devmirror)::

       sage -python
       >>> from lmfdb import db
       >>> db.ec_nfcurves.add_column("szpiro_ratio", "double precision",
       ...     description="Szpiro ratio log(Norm(D_min))/log(Norm(N)), NULL for curves with everywhere good reduction")

4. Upload the data and check that every row was set::

       >>> db.ec_nfcurves.update_from_file("ec_nfcurves_szpiro.txt")
       >>> db.ec_nfcurves.count({"szpiro_ratio": {"$exists": True}})
       >>> db.ec_nfcurves.count() - db.ec_nfcurves.count({"conductor_norm": 1})  # same number
       >>> db.ec_nfcurves.count({"conductor_norm": 1, "szpiro_ratio": {"$exists": True}})  # 0

   (``update_from_file`` merges into a new table and swaps it in, so it
   can be undone with ``reload_revert``.)

5. Create the index backing the new range search and sort.  Do this
   *after* the upload: the swap in step 4 rebuilds every index of the
   table from scratch, so an index created first would be built twice::

       >>> szpiro_sort = ["szpiro_ratio", "degree", "signature", "abs_disc",
       ...                "field_label", "conductor_norm", "conductor_label",
       ...                "iso_nlabel", "number"]
       >>> if "ec_nfcurves_szpiro_ratio_sort" not in db.ec_nfcurves.list_indexes():
       ...     db.ec_nfcurves.create_index(szpiro_sort, name="ec_nfcurves_szpiro_ratio_sort")

   The column list is exactly the sort tuple registered for "Szpiro
   ratio" in ``ECNFSearchArray.sorts``.  Use ``create_index`` rather
   than raw SQL: it records the definition in ``meta_indexes``, which is
   what lets later reloads rebuild the index.  Then check that it is
   there and that the planner uses it::

       >>> db.ec_nfcurves.list_indexes(verbose=True)
       >>> db.ec_nfcurves.analyze({}, projection=["label", "szpiro_ratio"],
       ...                        limit=50, sort=szpiro_sort, explain_only=True)
       >>> db.ec_nfcurves.analyze({"szpiro_ratio": {"$gte": 6, "$lte": 7}},
       ...                        projection=["label", "szpiro_ratio"],
       ...                        limit=50, sort=szpiro_sort, explain_only=True)

   Both plans should use ec_nfcurves_szpiro_ratio_sort instead of a
   sequential scan followed by a sort.  Do not restart the website until
   the index has finished building.

6. Restart/reload **every** web worker, so that HAVE_SZPIRO_RATIO, the
   result columns, the search boxes and the sort choices are rebuilt.

7. Smoke test display, search and sort: /EllipticCurve/2.2.5.1/31.1/a/1
   shows a Szpiro ratio of 1.0; /EllipticCurve/?field=2.2.5.1&szpiro_ratio=0.5-1.5
   contains it and ...&szpiro_ratio=1.1-1.5 does not; and
   /EllipticCurve/?sort_order=szpiro_ratio returns promptly.
"""
import argparse
import os
import random
import sys
import tempfile
from math import log

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from lmfdb import db


def min_disc_norm(rec):
    """Norm of the minimal discriminant ideal, computed from local_data."""
    return prod_pow([(ld["normp"], ld["ord_disc"]) for ld in rec["local_data"]])


def min_disc_norm_from_normdisc(rec):
    """Norm of the minimal discriminant ideal, computed from normdisc.

    The stored model is minimal outside the primes in non_min_p, at each
    of which the valuation of its discriminant is 12 more than that of
    the minimal discriminant.
    """
    normdisc = abs(int(rec["normdisc"]))
    D = normdisc
    for p in rec["non_min_p"]:
        normp = None
        for ld in rec["local_data"]:
            if ld["p"] == p:
                normp = ld["normp"]
                break
        if normp is None:
            raise ValueError(
                "%s: no local_data entry for the non-minimal prime %s "
                "(local_data covers %s)"
                % (rec["label"], p, ", ".join(ld["p"] for ld in rec["local_data"]) or "no primes"))
        D, r = divmod(D, normp**12)
        if r:
            raise ValueError(
                "%s: |normdisc| = %s is not divisible by normp^12 = %s^12 at the "
                "non-minimal prime %s" % (rec["label"], normdisc, normp, p))
    return D


def szpiro_ratio(Dnorm, Nnorm, label=None):
    """log(Dnorm)/log(Nnorm), or None if not defined (trivial conductor).

    ``Dnorm`` is the norm of the minimal discriminant ideal and ``Nnorm``
    the norm of the conductor; both must be positive integers.  ``label``
    is only used to make the error messages identify the offending curve.
    """
    where = "" if label is None else "%s: " % label
    if Dnorm <= 0:
        raise ValueError("%sminimal discriminant norm is %s, expected a positive integer"
                         % (where, Dnorm))
    if Nnorm <= 0:
        raise ValueError("%sconductor norm is %s, expected a positive integer"
                         % (where, Nnorm))
    if Nnorm == 1:
        # everywhere good reduction: D_min = (1) too, sigma undefined
        if Dnorm != 1:
            raise ValueError("%sconductor norm is 1 but the minimal discriminant has norm %s"
                             % (where, Dnorm))
        return None
    return log(Dnorm) / log(Nnorm)


def prod_pow(pairs):
    D = 1
    for p, e in pairs:
        D *= p**e
    return D


def generate(outfile, limit=None, sample_check=1000, verify_count=0, seed=None):
    """Write the szpiro_ratio data file for ec_nfcurves, or fail without writing it.

    Rows go to a temporary file in the same directory as ``outfile``,
    which is replaced only once everything below has succeeded; on any
    failure the temporary file is removed and ``outfile`` is untouched.
    """
    rand = random.Random(seed)

    total = db.ec_nfcurves.count()
    minimal_count = db.ec_nfcurves.count({"non_min_p": []})
    nonminimal_count = db.ec_nfcurves.count({"non_min_p": {"$ne": []}})
    if minimal_count + nonminimal_count != total:
        raise RuntimeError(
            "ec_nfcurves has %s rows, but %s have non_min_p = [] and %s have "
            "non_min_p != []; the %s remaining rows (most likely NULL non_min_p) "
            "would be silently omitted"
            % (total, minimal_count, nonminimal_count,
               total - minimal_count - nonminimal_count))

    processed_minimal = minimal_count if limit is None else min(limit, minimal_count)
    processed_nonminimal = nonminimal_count if limit is None else min(limit, nonminimal_count)
    expected = processed_minimal + processed_nonminimal

    # Cross-check exactly this many minimal rows, at positions drawn up front,
    # rather than with a probability derived from the size of the whole table.
    target_checks = min(sample_check, processed_minimal)
    check_positions = set(rand.sample(range(processed_minimal), target_checks))

    directory = os.path.dirname(os.path.abspath(outfile))
    fd, tmpfile = tempfile.mkstemp(dir=directory, prefix=os.path.basename(outfile) + ".")
    try:
        nulls = written = checked = 0
        with os.fdopen(fd, "w") as F:
            F.write("label|szpiro_ratio\ntext|double precision\n\n")

            # Curves whose stored model is globally minimal: here
            # Norm(D_min) = |normdisc| and we do not need local_data.
            # The sampled positions are cross-checked against local_data.
            for i, rec in enumerate(db.ec_nfcurves.search(
                    {"non_min_p": []},
                    ["label", "conductor_norm", "normdisc"],
                    sort=[], limit=limit)):
                Dnorm = abs(int(rec["normdisc"]))
                sigma = szpiro_ratio(Dnorm, rec["conductor_norm"], rec["label"])
                if i in check_positions:
                    full = db.ec_nfcurves.lookup(rec["label"], ["label", "local_data", "non_min_p"])
                    from_local_data = min_disc_norm(full)
                    if from_local_data != Dnorm:
                        raise ValueError(
                            "%s: |normdisc| = %s but local_data gives Norm(D_min) = %s"
                            % (rec["label"], Dnorm, from_local_data))
                    checked += 1
                F.write("%s|%s\n" % (rec["label"], r"\N" if sigma is None else repr(sigma)))
                written += 1
                nulls += sigma is None
                if written % 100000 == 0:
                    print("%s/%s done" % (written, expected))

            # Curves stored with a non-minimal model: compute from
            # local_data and cross-check against normdisc.
            for rec in db.ec_nfcurves.search(
                    {"non_min_p": {"$ne": []}},
                    ["label", "conductor_norm", "normdisc", "non_min_p", "local_data"],
                    sort=[], limit=limit):
                Dnorm = min_disc_norm(rec)
                from_normdisc = min_disc_norm_from_normdisc(rec)
                if Dnorm != from_normdisc:
                    raise ValueError(
                        "%s: local_data gives Norm(D_min) = %s but normdisc gives %s"
                        % (rec["label"], Dnorm, from_normdisc))
                sigma = szpiro_ratio(Dnorm, rec["conductor_norm"], rec["label"])
                F.write("%s|%s\n" % (rec["label"], r"\N" if sigma is None else repr(sigma)))
                written += 1
                nulls += sigma is None

        if checked != target_checks:
            raise RuntimeError("asked for %s minimal-model cross-checks but made %s"
                               % (target_checks, checked))
        if written != expected:
            raise RuntimeError(
                "expected to write %s rows (%s minimal + %s non-minimal) but wrote %s"
                % (expected, processed_minimal, processed_nonminimal, written))
        print("Generated %s rows (%s NULL, i.e. everywhere good reduction)" % (written, nulls))
        print("Cross-checked %s minimal-model rows against local_data" % checked)

        # Verify before installing the file, so that a failure leaves nothing behind.
        if verify_count:
            verify(tmpfile, verify_count, rand=rand)

        # mkstemp creates the file 0600; the data file is meant to be readable
        # by whoever uploads it, as it would be if we had just opened outfile.
        os.chmod(tmpfile, 0o644)
        os.replace(tmpfile, outfile)
    except BaseException:
        if os.path.exists(tmpfile):
            os.unlink(tmpfile)
        raise
    print("Wrote %s" % outfile)


def verify(datafile, nchecks=20, rand=None):
    """Recompute szpiro_ratio for random rows of the output file from scratch.

    This is an independent check: the curve is rebuilt in Sage from its
    a-invariants and the norms of its conductor and minimal discriminant
    ideal are recomputed, without using conductor_norm, normdisc or
    local_data.
    """
    from sage.all import EllipticCurve
    from lmfdb.ecnf.WebEllipticCurve import FIELD, parse_ainvs

    if rand is None:
        rand = random.Random()
    with open(datafile) as F:
        lines = F.read().splitlines()[3:]
    if nchecks > len(lines):
        raise ValueError(
            "asked to verify %s rows from scratch, but the generated file has "
            "only %s data rows; use --verify %s or fewer (or raise --limit)"
            % (nchecks, len(lines), len(lines)))
    for line in rand.sample(lines, nchecks):
        label, _, sigma = line.partition("|")
        rec = db.ec_nfcurves.lookup(label, ["field_label", "ainvs", "base_change"])
        K = FIELD(rec["field_label"]).K()
        E = EllipticCurve(parse_ainvs(K, rec["ainvs"]))
        Nnorm = E.conductor().norm()
        Dnorm = E.minimal_discriminant_ideal().norm()
        if Nnorm == 1:
            if sigma != r"\N":
                raise ValueError("%s: has everywhere good reduction, so the file should "
                                 "give \\N, but it gives %s" % (label, sigma))
            print("%s: everywhere good reduction, NULL ok" % label)
        else:
            if sigma == r"\N":
                raise ValueError("%s: file gives \\N but the conductor has norm %s"
                                 % (label, Nnorm))
            recomputed = log(Dnorm) / log(Nnorm)
            if abs(recomputed - float(sigma)) >= 1e-12:
                raise ValueError("%s: file has %s but Sage gives %s"
                                 % (label, sigma, recomputed))
            print("%s: %s ok (Norm(D_min)=%s, Norm(N)=%s, base change of %s)"
                  % (label, sigma, Dnorm, Nnorm, rec["base_change"] or "nothing"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("outfile", help="output file (update_from_file format)")
    parser.add_argument("--limit", type=int, default=None,
                        help="only process this many rows from each query (sample run)")
    parser.add_argument("--sample-check", type=int, default=1000,
                        help="number of minimal-model rows to cross-check against local_data")
    parser.add_argument("--verify", type=int, default=0, metavar="N",
                        help="before installing the file, recompute N random rows from scratch with Sage")
    parser.add_argument("--seed", type=int, default=None,
                        help="seed for the rows sampled by --sample-check and --verify")
    args = parser.parse_args()
    for opt in ("limit", "sample_check", "verify"):
        value = getattr(args, opt)
        if value is not None and value < 0:
            parser.error("--%s must be nonnegative (got %s)" % (opt.replace("_", "-"), value))
    generate(args.outfile, limit=args.limit, sample_check=args.sample_check,
             verify_count=args.verify, seed=args.seed)
