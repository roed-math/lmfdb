"""
Incremental version of dump-group-names.py: only dump tex names that are
referenced by gps_groups.tex_name, gps_subgroup_search.subgroup_tex or
gps_subgroup_search.quotient_tex but have no row in gps_images (these show
up as '?' in subgroup diagrams, cf. https://github.com/LMFDB/lmfdb/issues/7028).

Reference counts are computed server-side (gps_subgroup_search has ~275
million rows, so iterating over it client-side is impractical) and names are
written most-referenced first, so a truncated batch does the most good.

Output (same formats as dump-group-names.py, consumed by eq.tex/dvipng and
load-new-imgs.py):
 - eqguts.tex: one $...$ formula per line
 - prettyindex: one [n, "name-with-doubled-backslashes"] per line, where n is
   the (1-based) line number in eqguts.tex, hence the page number in eq.dvi
   and the number in the eqn.png produced by dvipng.

After running this, follow the same steps as in Readme:
 - move eqguts.tex to the images directory
 - in the images directory run: latex eq.tex
 - in the images directory run: dvipng -D 120 -bg Transparent eq.dvi
   (existing gps_images rows were rendered at 120 dpi; dvipng's default of
   100 dpi produces smaller images that don't match the current diagrams)
 - run load-new-imgs.py from this directory
"""

import sys
import os
import re
from collections import Counter
HOME = os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'lmfdb'))
from lmfdb import db
from psycopg2.sql import SQL

refcounts = Counter()
for query in [
        "SELECT tex_name, COUNT(*) FROM gps_groups WHERE tex_name IS NOT NULL GROUP BY tex_name",
        "SELECT subgroup_tex, COUNT(*) FROM gps_subgroup_search WHERE subgroup_tex IS NOT NULL GROUP BY subgroup_tex",
        "SELECT quotient_tex, COUNT(*) FROM gps_subgroup_search WHERE quotient_tex IS NOT NULL GROUP BY quotient_tex"]:
    for name, n in db._execute(SQL(query)):
        refcounts[name] += n

existing = set(rec[0] for rec in db._execute(SQL("SELECT label FROM gps_images")))
missing = [name for name in refcounts if name and name not in existing]
missing.sort(key=lambda name: (-refcounts[name], name))
print("%d referenced tex names, %d missing from gps_images (%d references)"
      % (len(refcounts), len(missing), sum(refcounts[name] for name in missing)))

# Skip names using macros that latex cannot expand (broken tex names; the
# website's KaTeX macro list in lmfdb/templates/base.html cannot render these
# either, so they need fixing upstream rather than an image).  One bad formula
# would otherwise derail the whole latex run.
defined = set(re.findall(r"\\newcommand\{\\(\w+)\}",
                         open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "eq.tex")).read()))
standard = set("""times rtimes ltimes wr Gamma Sigma Omega Delta Lambda Phi Psi Pi Theta Xi Upsilon
alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi pi rho sigma tau upsilon
phi chi psi omega mathrm mathbb mathfrak mathcal textrm rm cdot ast circ""".split())
skipped = [name for name in missing
           if any(m not in defined and m not in standard for m in re.findall(r"\\([A-Za-z]+)", name))]
if skipped:
    missing = [name for name in missing if name not in set(skipped)]
    print("SKIPPING %d names using macros undefined in images/eq.tex (fix the tex names or the preamble):"
          % len(skipped))
    for name in skipped[:20]:
        print("   ", name)
    if len(skipped) > 20:
        print("    ... (%d more)" % (len(skipped) - 20))

count = 0
with open("eqguts.tex", "w") as eqguts:
    with open("prettyindex", "w") as prettyindex:
        for p in missing:
            pp = p.replace('\\', '\\\\')
            eqguts.write('$' + str(p) + '$\n')
            count += 1
            prettyindex.write('[%d, "%s"]\n' % (count, pp))

print("Max count is %d" % count)
