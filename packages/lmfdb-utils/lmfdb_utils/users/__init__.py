"""
User accounts: logging in, registration by invitation, and the permissions
(administrator, knowl reviewer) that editing knowls needs.

The accounts are stored in ``userdb.users`` (see :mod:`lmfdb_utils.schema`);
they can only be used when the website's database role may read and write
that table, so a read-only website shows everyone as anonymous.
"""

from flask import Blueprint

login_page = Blueprint("users", __name__, template_folder="templates")


def init_app(app, url_prefix="/users"):
    """
    Add the user pages (at ``url_prefix``) and logging in to the Flask
    application ``app``; called by :func:`lmfdb_utils.web.init_app`.
    """
    from . import main
    main.login_manager.init_app(app)
    app.context_processor(main.ctx_proc_userdata)
    app.register_blueprint(login_page, url_prefix=url_prefix)


def __getattr__(name):
    # admin_required, knowl_reviewer_required, ... are defined in main, which
    # adds the routes to login_page (so is imported once it exists)
    if name in ("admin_required", "knowl_reviewer_required", "housekeeping", "login_manager"):
        from . import main
        return getattr(main, name)
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
