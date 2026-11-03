"""
The user database moved to lmfdb-utils (lmfdb_utils.users.pwdmanager); this
module is kept so that ``from lmfdb.users.pwdmanager import userdb`` keeps
working in scripts.
"""

from lmfdb_utils.users.pwdmanager import userdb, LmfdbUser, LmfdbAnonymousUser

__all__ = ["userdb", "LmfdbUser", "LmfdbAnonymousUser"]
