"""
The LMFDB's user accounts are lmfdb-utils' (lmfdb_utils.users); lmfdb.users.main
adds the LMFDB's own user pages.

lmfdb.users.pwdmanager is the same module object as
lmfdb_utils.users.pwdmanager, so imports from it keep working.
"""

import sys

from lmfdb_utils.users import pwdmanager

sys.modules[__name__ + ".pwdmanager"] = pwdmanager

from .main import (  # noqa: E402
    login_page,
    login_manager,
    admin_required,
    knowl_reviewer_required,
    housekeeping,
)

__all__ = ["pwdmanager", "login_page", "login_manager", "admin_required",
           "knowl_reviewer_required", "housekeeping"]
