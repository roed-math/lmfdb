"""
The LMFDB's knowledge database is lmfdb-utils' (lmfdb_utils.knowledge, set up
by lmfdb_utils.web.init_app in lmfdb/app.py).

Its modules keep their old names: lmfdb.knowledge.knowl and
lmfdb.knowledge.main are the same module objects as lmfdb_utils.knowledge.knowl
and lmfdb_utils.knowledge.main, so imports from them (in the LMFDB and in
scripts) keep working, and patching them patches the code that runs.
"""

import sys

from lmfdb_utils.knowledge import knowledge_page, knowl, main

sys.modules[__name__ + ".knowl"] = knowl
sys.modules[__name__ + ".main"] = main

__all__ = ["knowledge_page", "knowl", "main"]
