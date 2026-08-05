"""
Incremental version of load-imgs.py, for use after dump-missing-group-names.py:
instead of rewriting the whole gps_images table via reload(), write a file
"imageadder" containing ONLY rows whose label is not yet in gps_images and
append them with copy_from().  Skips any name that acquired an image since
dump-missing-group-names.py was run.
"""

import sys
import os
import json
import base64
HOME = os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'lmfdb'))
from lmfdb import db
# psycodict's own serializer: it escapes the delimiter, backslashes, newlines,
# tabs and the null marker the way copy_from expects.
from psycodict.encoding import copy_dumps

existing = set(ent['label'] for ent in db.gps_images.search({}, ['label']))

# The whole upload file is built before the database is touched, so that a
# missing or unreadable png aborts the run rather than loading a partial batch.
count = 0
with open("prettyindex", "r", encoding="utf-8") as fn:
    with open("imageadder", "w", encoding="utf-8") as afile:
        afile.write('label|image\n')
        afile.write('text|text\n\n')
        for line in fn:
            num, label = json.loads(line)
            if label in existing:
                continue
            existing.add(label)  # also guards against repeats in prettyindex
            with open('images/eq%d.png' % num, "rb") as png:
                image = 'data:image/png;base64,' + base64.b64encode(png.read()).decode("utf-8")
            afile.write("|".join([copy_dumps(label, "text", sep="|"),
                                  copy_dumps(image, "text", sep="|")]) + "\n")
            count += 1

print("Loaded %d new images" % count)

if count:
    db.gps_images.copy_from('imageadder')
else:
    print("Nothing new to load; gps_images left untouched")
