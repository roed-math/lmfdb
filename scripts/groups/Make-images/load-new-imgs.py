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

existing = set(ent['label'] for ent in db.gps_images.search({}, ['label']))

imdict = {}
with open("prettyindex", "r") as fn:
    for line in fn.readlines():
        l = json.loads(line)
        if l[1] in existing:
            continue
        fn2 = 'images/eq%d.png' % l[0]
        imdict[l[1]] = 'data:image/png;base64,' + base64.b64encode(open(fn2, "rb").read()).decode("utf-8")

print("Loaded %d new images" % len(imdict))

with open("imageadder", "w") as afile:
    afile.write('label|image\n')
    afile.write('text|text\n\n')
    for key, value in imdict.items():
        afile.write(key.replace('\\', '\\\\') + '|' + value.replace('\\', '\\\\'))
        afile.write('\n')

db.gps_images.copy_from('imageadder')
