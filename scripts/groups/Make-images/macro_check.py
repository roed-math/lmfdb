"""Preflight check keeping images/eq.tex in sync with the site-wide KaTeX
macro list in lmfdb/templates/base.html.

Group tex names (gps_groups.tex_name, gps_subgroup_search.subgroup_tex and
quotient_tex) are rendered two ways: by KaTeX on the website, using the macros
in base.html, and by latex+dvipng here, using the preamble in images/eq.tex.
If the two macro sets drift apart, names using a KaTeX-only macro render fine
on group pages but are classified as unrenderable by
dump-missing-group-names.py and silently dropped from the image set (showing
up as '?' in subgroup diagrams), while an eq.tex-only macro would produce
images for names the website itself cannot typeset inline.  This module makes
that drift loud: dump-missing-group-names.py aborts if the sets disagree, and
the check can be run standalone with

    sage -python macro_check.py

Only macro NAMES are compared.  A few bodies differ on purpose (e.g. \\GOPlus
is GO^+ in eq.tex but O^+ in KaTeX): the 733K images already in gps_images
were rendered with the eq.tex bodies, and new images must stay consistent
with them, so do not "fix" a body difference without rerendering everything.
"""
import os
import re
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
EQ_TEX = os.path.join(THIS_DIR, "images", "eq.tex")
# scripts/groups/Make-images -> repository root -> lmfdb/templates/base.html
BASE_HTML = os.path.join(THIS_DIR, "..", "..", "..", "lmfdb", "templates", "base.html")

# KaTeX macros from base.html that are deliberately NOT in eq.tex: number
# sets, operator names and helper macros that never occur in group tex names
# (verified against all 1,015,994 names referenced by gps_groups and
# gps_subgroup_search on 2026-07-19: none of these appeared in any name).
# When a new GROUP-NAME macro is added to base.html it does NOT belong here:
# add it to images/eq.tex instead, so images can be generated for names
# using it.
NON_GROUP_MACROS = {
    "C", "F", "H", "HH", "Q", "R", "integers",  # number sets and friends
    "Aut", "End", "Gal", "Hom", "Ord", "Out", "Pic", "Reg", "Res",
    "Spec", "Sym", "sgn", "trace",  # \operatorname-style operators
    "card", "classgroup", "ideal", "mathstrut", "modstar",  # helpers (take arguments)
}

# LaTeX/KaTeX built-ins allowed in tex names without a \newcommand anywhere
# (used by dump-missing-group-names.py when classifying names as renderable).
STANDARD_MACROS = set("""times rtimes ltimes wr Gamma Sigma Omega Delta Lambda Phi Psi Pi Theta Xi Upsilon
alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi pi rho sigma tau upsilon
phi chi psi omega mathrm mathbb mathfrak mathcal textrm rm cdot ast circ""".split())


def katex_macros(path=BASE_HTML):
    """Names of the macros defined in base.html's katexOpts macros map."""
    macros = set(re.findall(r'"\\\\(\w+)"\s*:', open(path).read()))
    if not macros:
        raise RuntimeError("no KaTeX macros found in %s -- did the katexOpts "
                           "format change? Update macro_check.py." % path)
    return macros


def eqtex_macros(path=EQ_TEX):
    """Names of the macros defined in the eq.tex preamble."""
    macros = set(re.findall(r"\\(?:re)?newcommand\{\\(\w+)\}", open(path).read()))
    if not macros:
        raise RuntimeError("no \\newcommand definitions found in %s" % path)
    return macros


def check(eqtex_path=EQ_TEX, base_html_path=BASE_HTML):
    """Return a list of human-readable problem descriptions (empty = in sync)."""
    katex = katex_macros(base_html_path)
    eqtex = eqtex_macros(eqtex_path)
    problems = []
    missing = katex - eqtex - NON_GROUP_MACROS
    if missing:
        problems.append(
            "defined in base.html KaTeX but not in images/eq.tex: %s\n"
            "  -> names using these render on the website but would be dropped\n"
            "     from image generation; add them to images/eq.tex (or, ONLY if\n"
            "     they can never occur in a group name, to NON_GROUP_MACROS in\n"
            "     macro_check.py)." % ", ".join("\\" + m for m in sorted(missing)))
    extra = eqtex - katex
    if extra:
        problems.append(
            "defined in images/eq.tex but not in base.html KaTeX: %s\n"
            "  -> images could be generated for names the website cannot render\n"
            "     inline; add the macros to the katexOpts list in\n"
            "     lmfdb/templates/base.html." % ", ".join("\\" + m for m in sorted(extra)))
    shadowed = NON_GROUP_MACROS & eqtex
    if shadowed:
        problems.append(
            "listed in NON_GROUP_MACROS but also defined in images/eq.tex: %s\n"
            "  -> remove them from NON_GROUP_MACROS in macro_check.py."
            % ", ".join("\\" + m for m in sorted(shadowed)))
    return problems


def main():
    problems = check()
    if problems:
        print("macro_check: images/eq.tex and lmfdb/templates/base.html are OUT OF SYNC")
        for p in problems:
            print("* " + p)
        return 1
    print("macro_check: OK -- images/eq.tex covers all %d group-name macros of the"
          " %d in base.html's KaTeX list (%d deliberately excluded as non-group)"
          % (len(katex_macros() - NON_GROUP_MACROS), len(katex_macros()),
             len(NON_GROUP_MACROS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
