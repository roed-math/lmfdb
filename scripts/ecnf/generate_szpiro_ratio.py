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
above are computed and checked against each other.  A random sample of
minimal rows is cross-checked against local_data as well.

Run from the top-level lmfdb directory (requires a working config.ini;
read access is enough):

    sage -python scripts/ecnf/generate_szpiro_ratio.py ec_nfcurves_szpiro.txt

Optional flags: ``--limit N`` (sample run), ``--sample-check N`` (number
of minimal-model rows to cross-check against local_data, default 1000),
``--verify N`` (recompute N random rows from scratch with Sage from the
a-invariants; slow but fully independent).

The output file is in the format expected by ``update_from_file``.  To
upload (needs an account with write access; not possible on devmirror):

    sage -python
    >>> from lmfdb import db
    >>> db.ec_nfcurves.add_column("szpiro_ratio", "double precision",
    ...     description="Szpiro ratio log(Norm(D_min))/log(Norm(N)), NULL for curves with everywhere good reduction")
    >>> db.ec_nfcurves.update_from_file("ec_nfcurves_szpiro.txt")
"""
import argparse
import os
import sys
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
    D = abs(int(rec["normdisc"]))
    for p in rec["non_min_p"]:
        normp = next(ld["normp"] for ld in rec["local_data"] if ld["p"] == p)
        D, r = divmod(D, normp**12)
        assert r == 0, "normdisc not divisible by normp^12 for %s" % rec["label"]
    return D


def szpiro_ratio(Dnorm, Nnorm):
    """log(Dnorm)/log(Nnorm), or None if not defined (trivial conductor)."""
    if Nnorm == 1:
        # everywhere good reduction: D_min = (1) too, sigma undefined
        assert Dnorm == 1, "conductor norm 1 but Dnorm = %s" % Dnorm
        return None
    return log(Dnorm) / log(Nnorm)


def prod_pow(pairs):
    D = 1
    for p, e in pairs:
        D *= p**e
    return D


def generate(outfile, limit=None, sample_check=1000):
    from random import randrange

    total = db.ec_nfcurves.count()
    nulls = written = 0
    check_freq = max(1, total // sample_check) if sample_check else 0
    with open(outfile, "w") as F:
        F.write("label|szpiro_ratio\ntext|double precision\n\n")

        # Curves whose stored model is globally minimal: here
        # Norm(D_min) = |normdisc| and we do not need local_data.
        # A random sample is cross-checked against local_data.
        checked = 0
        for i, rec in enumerate(db.ec_nfcurves.search(
                {"non_min_p": []},
                ["label", "conductor_norm", "normdisc"],
                sort=[], limit=limit)):
            Dnorm = abs(int(rec["normdisc"]))
            sigma = szpiro_ratio(Dnorm, rec["conductor_norm"])
            if check_freq and i % check_freq == randrange(check_freq):
                full = db.ec_nfcurves.lookup(rec["label"], ["local_data", "non_min_p"])
                assert min_disc_norm(full) == Dnorm, \
                    "normdisc inconsistent with local_data for %s" % rec["label"]
                checked += 1
            F.write("%s|%s\n" % (rec["label"], r"\N" if sigma is None else repr(sigma)))
            written += 1
            nulls += sigma is None
            if written % 100000 == 0:
                print("%s/%s done" % (written, total))

        # Curves stored with a non-minimal model: compute from
        # local_data and cross-check against normdisc.
        for rec in db.ec_nfcurves.search(
                {"non_min_p": {"$ne": []}},
                ["label", "conductor_norm", "normdisc", "non_min_p", "local_data"],
                sort=[], limit=limit):
            Dnorm = min_disc_norm(rec)
            assert Dnorm == min_disc_norm_from_normdisc(rec), \
                "normdisc inconsistent with local_data for %s" % rec["label"]
            sigma = szpiro_ratio(Dnorm, rec["conductor_norm"])
            F.write("%s|%s\n" % (rec["label"], r"\N" if sigma is None else repr(sigma)))
            written += 1
            nulls += sigma is None
    print("Wrote %s rows (%s NULL, i.e. everywhere good reduction) to %s"
          % (written, nulls, outfile))
    print("Cross-checked %s minimal-model rows against local_data" % checked)
    if limit is None and written != total:
        print("WARNING: table has %s rows but %s were written" % (total, written))


def verify(datafile, nchecks=20):
    """Recompute szpiro_ratio for random rows of the output file from scratch.

    This is an independent check: the curve is rebuilt in Sage from its
    a-invariants and the norms of its conductor and minimal discriminant
    ideal are recomputed, without using conductor_norm, normdisc or
    local_data.
    """
    from random import sample
    from sage.all import EllipticCurve
    from lmfdb.ecnf.WebEllipticCurve import FIELD, parse_ainvs

    with open(datafile) as F:
        lines = F.read().splitlines()[3:]
    for line in sample(lines, nchecks):
        label, _, sigma = line.partition("|")
        rec = db.ec_nfcurves.lookup(label, ["field_label", "ainvs", "base_change"])
        K = FIELD(rec["field_label"]).K()
        E = EllipticCurve(parse_ainvs(K, rec["ainvs"]))
        Nnorm = E.conductor().norm()
        Dnorm = E.minimal_discriminant_ideal().norm()
        if Nnorm == 1:
            assert sigma == r"\N", "%s: expected NULL, file has %s" % (label, sigma)
            print("%s: everywhere good reduction, NULL ok" % label)
        else:
            recomputed = log(Dnorm) / log(Nnorm)
            assert abs(recomputed - float(sigma)) < 1e-12, \
                "%s: file has %s but Sage gives %s" % (label, sigma, recomputed)
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
                        help="after generating, recompute N random rows from scratch with Sage")
    args = parser.parse_args()
    generate(args.outfile, limit=args.limit, sample_check=args.sample_check)
    if args.verify:
        verify(args.outfile, args.verify)
