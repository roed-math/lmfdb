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
import json
from collections import Counter
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import macro_check

# Preflight (before connecting or querying): images/eq.tex must define every
# group-name macro in the site-wide KaTeX list, else names the website can
# render would be misclassified as broken and silently skipped below.
problems = macro_check.check()
if problems:
    sys.exit("images/eq.tex is out of sync with the KaTeX macros in "
             "lmfdb/templates/base.html:\n"
             + "\n".join("* " + p for p in problems))

HOME = os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'lmfdb'))
from lmfdb import db
# Not psycopg2/psycopg directly: composables handed to db._execute must come
# from whichever driver the installed psycodict uses (both may be importable).
from lmfdb.utils.psycopg_compat import SQL

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

# Skip names using macros that latex cannot expand (broken tex names; thanks
# to the preflight above, these are exactly the names the website's KaTeX
# macro list in lmfdb/templates/base.html cannot render either, so they need
# fixing upstream rather than an image).  One bad formula would otherwise
# derail the whole latex run.
defined = macro_check.eqtex_macros()
standard = macro_check.STANDARD_MACROS
renderable, skipped = [], []
for name in missing:
    macros = re.findall(r"\\([A-Za-z]+)", name)
    if all(m in defined or m in standard for m in macros):
        renderable.append(name)
    else:
        skipped.append(name)
missing = renderable
if skipped:
    print("SKIPPING %d names using macros undefined in images/eq.tex (fix the tex names or the preamble):"
          % len(skipped))
    for name in skipped[:20]:
        print("   ", name)
    if len(skipped) > 20:
        print("    ... (%d more)" % (len(skipped) - 20))

count = 0
with open("eqguts.tex", "w", encoding="utf-8") as eqguts:
    with open("prettyindex", "w", encoding="utf-8") as prettyindex:
        for p in missing:
            eqguts.write('$' + p + '$\n')
            count += 1
            # json rather than hand-rolled quoting: it escapes quotes, tabs and
            # control characters as well as the backslashes of the tex name.
            json.dump([count, p], prettyindex, ensure_ascii=False)
            prettyindex.write("\n")

print("Max count is %d" % count)
