"""
Creating the tables of the knowledge database and the user accounts in a new
database, and granting the website's role access to them.

psycodict creates its own metadata tables (``PostgresDatabase(create=True)``)
and the tables holding a website's data (``db.create_table``); the tables
here are the ones :mod:`lmfdb_utils.knowledge` and :mod:`lmfdb_utils.users`
use, with the same layout as in the LMFDB:

- ``kwl_knowls``: every version of every knowl (the latest version of a knowl
  is the one with the largest ``timestamp``);
- ``kwl_locks``: who is editing which knowl;
- ``userdb.users``: user accounts;
- ``userdb.tokens``: the registration links created by administrators.

For example, connected as the role owning the database::

    from lmfdb_utils.schema import create_tables, grant_website_access, add_user
    create_tables(db)
    grant_website_access(db, "mysite_web")
    add_user(db, "admin", "a password", full_name="An Administrator", admin=True)
"""

from psycodict import DelayCommit, SQL, Identifier

KNOWL_TABLES = {
    "kwl_knowls": """
CREATE TABLE kwl_knowls (
    id text NOT NULL,
    cat text,
    title text NOT NULL,
    content text NOT NULL,
    last_author text,
    timestamp timestamp without time zone NOT NULL,
    status smallint DEFAULT 0,
    type smallint DEFAULT 0,
    links text[],
    defines text[],
    source text,
    source_name text,
    reviewer text,
    reviewer_timestamp timestamp without time zone,
    authors text[],
    _keywords text[]
)""",
    "kwl_locks": """
CREATE TABLE kwl_locks (
    id text,
    timestamp timestamp without time zone,
    username text
)""",
}

KNOWL_INDEXES = [
    "CREATE INDEX kwl_knowls_id_timestamp ON kwl_knowls (id, timestamp DESC)",
    "CREATE INDEX kwl_knowls_keywords ON kwl_knowls USING gin (_keywords)",
    "CREATE INDEX kwl_locks_id ON kwl_locks (id, timestamp)",
]

USER_TABLES = {
    "users": """
CREATE TABLE userdb.users (
    username text PRIMARY KEY,
    password text,
    bcpassword text,
    created timestamp without time zone,
    full_name text,
    about text,
    url text,
    admin boolean DEFAULT false,
    knowl_reviewer boolean DEFAULT false,
    color_scheme smallint
)""",
    "tokens": """
CREATE TABLE userdb.tokens (
    id text PRIMARY KEY,
    expire timestamp without time zone
)""",
}


def _table_exists(db, name, schema="public"):
    return bool(db._execute(
        SQL("SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s"),
        [schema, name],
    ).fetchone())


def create_knowl_tables(db):
    """
    Create the tables of the knowledge database (``kwl_knowls`` and
    ``kwl_locks``) and their indexes, unless they exist already.
    """
    with DelayCommit(db, silence=True):
        for name, creator in KNOWL_TABLES.items():
            if not _table_exists(db, name):
                db._execute(SQL(creator))
                if name == "kwl_knowls":
                    for index in KNOWL_INDEXES[:2]:
                        db._execute(SQL(index))
                else:
                    db._execute(SQL(KNOWL_INDEXES[2]))
                print("Table %s created" % name)


def create_user_tables(db):
    """
    Create the schema ``userdb`` and its tables ``users`` and ``tokens``,
    unless they exist already.
    """
    with DelayCommit(db, silence=True):
        db._execute(SQL("CREATE SCHEMA IF NOT EXISTS userdb"))
        for name, creator in USER_TABLES.items():
            if not _table_exists(db, name, schema="userdb"):
                db._execute(SQL(creator))
                print("Table userdb.%s created" % name)


def create_tables(db):
    """
    Create the tables of the knowledge database and the user accounts (see
    :func:`create_knowl_tables` and :func:`create_user_tables`).
    """
    create_knowl_tables(db)
    create_user_tables(db)


def grant_website_access(db, role, edit=True):
    """
    Grant the role ``role``, used by the website, access to the knowls and
    users.

    INPUT:

    - ``db`` -- the database, connected as a role allowed to grant these
      privileges (such as the owner of the tables)
    - ``role`` -- the name of the role the website connects as
    - ``edit`` -- if True (the default), the website can edit knowls and
      users can log in (the role may read and write the tables); if False,
      it can only show the knowls, and everyone is anonymous.  The
      LMFDB uses ``edit=False`` for www.lmfdb.org and ``edit=True`` for
      beta.lmfdb.org.

    The website's data tables are granted by psycodict's grant policy (see
    ``psycodict.grants``) when they are created.
    """
    ident = Identifier(role)
    with DelayCommit(db, silence=True):
        db._execute(SQL("GRANT USAGE ON SCHEMA userdb TO {0}").format(ident))
        if edit:
            db._execute(SQL("GRANT SELECT, INSERT, UPDATE ON kwl_knowls, kwl_locks TO {0}").format(ident))
            db._execute(SQL("GRANT SELECT, INSERT, UPDATE ON userdb.users TO {0}").format(ident))
            db._execute(SQL("GRANT SELECT, INSERT, DELETE ON userdb.tokens TO {0}").format(ident))
        else:
            db._execute(SQL("GRANT SELECT ON kwl_knowls TO {0}").format(ident))
            # only the names of users, which are shown as the authors of knowls
            db._execute(SQL("GRANT SELECT (username, full_name) ON userdb.users TO {0}").format(ident))
    print("Granted %s access to the knowls and users (%s)" % (role, "read and write" if edit else "read only"))


def add_user(db, username, password, full_name=None, admin=False, knowl_reviewer=False):
    """
    Create a user account, for example the first administrator (who can then
    invite others with registration links, at ``/users/register/new``).

    INPUT:

    - ``db`` -- the database, connected as a role that may write ``userdb.users``
    - ``username`` -- the user's login name (letters, digits, ``.``, ``_`` and ``-``)
    - ``password`` -- the user's password
    - ``full_name`` -- the name shown as the author of knowls
    - ``admin`` -- whether the user is an administrator (who can delete knowls
      and create registration links)
    - ``knowl_reviewer`` -- whether the user can mark knowls as reviewed
    """
    from .users.main import allowed_usernames
    from .users.pwdmanager import PostgresUserTable
    if not allowed_usernames.match(username):
        raise ValueError("Usernames consist of letters, digits, '.', '_' and '-'")
    users = PostgresUserTable(db)
    if not users.can_read_write_userdb():
        raise RuntimeError("This connection cannot write userdb.users")
    users.new_user(username, pwd=password, full_name=full_name)
    db._execute(
        SQL("UPDATE userdb.users SET (admin, knowl_reviewer) = (%s, %s) WHERE username = %s"),
        [admin, knowl_reviewer, username],
    )
    print("User %s created" % username)
