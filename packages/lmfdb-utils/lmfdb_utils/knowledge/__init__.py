"""
The knowledge database: knowls, the short definitions and explanations that
appear when clicked, and the pages for showing, editing, reviewing and
searching them (at ``/knowledge``).

Templates include knowls with the ``KNOWL``, ``KNOWL_INC`` and related
macros of ``knowl-defs.html``, which every page imports.  The knowls are
stored in the table ``kwl_knowls`` (see :mod:`lmfdb_utils.schema`).
"""

from flask import Blueprint

knowledge_page = Blueprint("knowledge", __name__, template_folder="templates")


def init_app(app, url_prefix="/knowledge"):
    """
    Add the knowledge pages (at ``url_prefix``) and the knowl template
    helpers to the Flask application ``app``; called by
    :func:`lmfdb_utils.web.init_app`.
    """
    from . import main
    app.context_processor(main.ctx_knowledge)
    app.template_filter("render_knowl")(main.render_knowl_in_template)
    app.jinja_env.tests["knowl_type"] = main.test_knowl_type
    app.register_blueprint(knowledge_page, url_prefix=url_prefix)
