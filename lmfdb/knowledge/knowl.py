"""
The knowledge database moved to lmfdb-utils (lmfdb_utils.knowledge.knowl);
this module is kept so that ``from lmfdb.knowledge.knowl import knowldb`` keeps
working in scripts.
"""

from lmfdb_utils.knowledge.knowl import (
    Knowl,
    KnowlBackend,
    bad_knowl_id_reason,
    knowl_exists,
    knowl_status_code,
    knowl_title,
    knowl_type_code,
    knowldb,
)

__all__ = [
    "Knowl",
    "KnowlBackend",
    "bad_knowl_id_reason",
    "knowl_exists",
    "knowl_status_code",
    "knowl_title",
    "knowl_type_code",
    "knowldb",
]
