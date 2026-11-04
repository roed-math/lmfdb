"""
Setting up a Flask application to use lmfdb-utils.

:func:`init_app` gives an application everything the utilities' pages need:

- the templates in ``lmfdb_utils/templates`` (the page layout, search results,
  statistics, knowls, ...) and the static files in ``lmfdb_utils/static``
  (scripts, style sheets and images);
- the style sheet ``/style.css``, in the color scheme chosen by the request,
  the user or the site;
- the variables and filters these templates use;
- the knowledge database (``/knowledge``) and user accounts (``/users``).

The application's own templates and static files take precedence: a website
customizes a page by putting a template of the same name in its own
``templates`` folder (for example ``homepage.html``, which sets the logo and
footer by extending ``lmfdb_utils/layout.html``), and replaces a static file
the same way.

The application must also provide an ``index`` endpoint (the home page,
linked from the header of every page).

A site without a database (one that does not override ``Site.db``) gets the
layout, style sheet and static files, but no knowls, and nobody can log in.

There is one site per Python process: the site installed by ``init_app``
(:func:`~lmfdb_utils.site.current_site`), and the knowledge and user
databases, markdown converter and sidebar built from it, are shared by every
application in the process.  Run different websites in different processes.
"""

import os
from datetime import datetime
from urllib.parse import urlencode as _urlencode, urlparse, urlunparse

from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    make_response,
    render_template,
    request,
    send_from_directory,
)
from werkzeug.exceptions import NotFound

from .site import current_site, set_current_site

STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Only used for its templates: the static files are served from the
# application's own /static/ address (see _serve_static).
lmfdb_utils_page = Blueprint("lmfdb_utils", __name__, template_folder="templates")


def init_app(app, site=None):
    """
    Set up the Flask application ``app`` to use lmfdb-utils.

    INPUT:

    - ``app`` -- a Flask application
    - ``site`` -- an instance of a subclass of :class:`~lmfdb_utils.site.Site`
      describing the website, installed with
      :func:`~lmfdb_utils.site.set_current_site`; if omitted, the site
      installed already is used

    Call this when creating the application, before registering the website's
    own context processors (so that they can override the defaults set here).
    """
    if site is not None:
        set_current_site(site)
    app.register_blueprint(lmfdb_utils_page)
    _serve_static(app)

    # remove the line breaks after block tags, and allow break, continue and do
    app.jinja_env.trim_blocks = True
    app.jinja_env.add_extension("jinja2.ext.loopcontrols")
    app.jinja_env.add_extension("jinja2.ext.do")

    app.context_processor(default_context)
    app.context_processor(add_colors)
    app.context_processor(inject_sidebar)
    app.template_filter("fmtdatetime")(fmtdatetime)
    app.template_filter("nl2br")(nl2br)
    app.template_filter("urlencode")(urlencode)
    app.before_request(get_menu_cookie)
    app.add_url_rule("/style.css", "css", css)

    from .users import init_app as init_users
    from .knowledge import init_app as init_knowledge
    init_users(app)
    init_knowledge(app)


def _serve_static(app):
    """
    Serve the static files of lmfdb-utils at the application's /static/
    address, after the application's own: a file in the application's static
    folder replaces the one of the same name here.
    """
    def static(filename):
        folders = [app.static_folder] if app.static_folder else []
        for folder in folders + [STATIC_FOLDER]:
            try:
                return send_from_directory(folder, filename, max_age=app.get_send_file_max_age(filename))
            except NotFound:
                pass
        abort(404)

    if "static" in app.view_functions:
        app.view_functions["static"] = static
    else:
        app.add_url_rule("/static/<path:filename>", "static", static)


##############################
#    Template variables      #
##############################


def modify_url(**replace):
    """
    The address of the current request, with some of its parts replaced (as
    in ``urllib.parse.ParseResult._replace``).  ``query_add`` gives a query
    string to put in front of the current one.
    """
    url = request.url
    if url.startswith("https, "):
        # Cocalc weirdness that lets them serve pages on https from within a project
        url = url[7:]
    urlparts = urlparse(url)
    if "query_add" in replace:
        assert "query" not in replace
        if urlparts.query:
            replace["query"] = replace.pop("query_add") + "&" + urlparts.query
        else:
            replace["query"] = replace.pop("query_add")
    urlparts = urlparts._replace(**replace)
    return urlunparse(urlparts)


def default_context():
    """
    The variables available in every template:

    * ``info`` (an empty dictionary), ``body_class`` and ``bread`` (the
      breadcrumbs, a list of pairs (name, url), or None), which pages set;
    * ``title`` (the site's name by default) and ``meta_description``;
    * ``site``, the :class:`~lmfdb_utils.site.Site`, and ``feedbackpage``;
    * ``DEBUG`` and ``BETA``, saying whether Flask runs in debug mode and
      whether the site is in beta (see :meth:`~lmfdb_utils.site.Site.is_beta`);
    * ``CodeSnippet``, ``modify_url``, ``pluralize`` and ``zip``.
    """
    from .place_code import CodeSnippet
    from .utilities import pluralize
    site = current_site()
    return {
        "info": {},
        "body_class": "",
        "bread": None,
        "title": site.name,
        "meta_description": site.meta_description,
        "site": site,
        "feedbackpage": site.feedback_url,
        "DEBUG": current_app.debug,
        "BETA": site.is_beta(),
        "CodeSnippet": CodeSnippet,
        "modify_url": modify_url,
        "pluralize": pluralize,
        "zip": zip,
    }


def current_color_scheme():
    """
    The color scheme for the current request: the one given by the ``color``
    argument of the request, otherwise the one chosen by the user (if logged
    in), otherwise the site's default.
    """
    schemes = current_site().color_schemes()
    color = request.args.get("color")
    if color and color.isdigit():
        color = int(color)
    if color not in schemes:
        color = None
    if color is None:
        from flask_login import current_user
        userid = current_user.get_id()
        if userid is not None:
            from .users.pwdmanager import userdb
            color = userdb.lookup(userid).get("color_scheme")
        if color not in schemes:
            color = current_site().default_color
    return schemes[color]


def add_colors():
    return {"color": current_color_scheme().dict()}


def inject_sidebar():
    from .sidebar import get_sidebar
    return {"sidebar": get_sidebar()}


def get_menu_cookie():
    """
    Whether to show the sidebar menu, as set by the menu toggle
    """
    g.show_menu = str(request.cookies.get("showmenu")) != "False"


def css():
    """
    The style sheet, in the current color scheme (see current_color_scheme)
    """
    response = make_response(render_template("style.css"))
    response.headers["Content-type"] = "text/css"
    # don't cache css file, if in debug mode.
    if current_app.debug:
        response.headers["Cache-Control"] = "no-cache, no-store"
    else:
        response.headers["Cache-Control"] = "public, max-age=600"
    return response


##############################
#      Jinja formatters      #
##############################


def fmtdatetime(value, format="%Y-%m-%d %H:%M:%S"):
    """
    Format a datetime in a template: ``{{ value|fmtdatetime }}``, or
    ``{{ value|fmtdatetime('%H:%M:%S') }}``
    """
    if isinstance(value, datetime):
        return value.strftime(format)
    else:
        return "-"


def nl2br(s):
    """
    Turn the newlines in a string into HTML line breaks
    """
    return s.replace("\n", "<br/>\n")


def urlencode(kwargs):
    """
    Encode a dictionary as a query string
    """
    return _urlencode(kwargs)
