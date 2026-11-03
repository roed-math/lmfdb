"""
The LMFDB's knowledge database is lmfdb-utils' (lmfdb_utils.knowledge, set up
by lmfdb_utils.web.init_app in lmfdb/app.py).  ``lmfdb.knowledge.knowl`` is
kept for scripts that import the knowledge database from there.
"""

from lmfdb_utils.knowledge import knowledge_page

assert knowledge_page  # silence pyflakes
