"""
Tests for lmfdb-utils on its own, without the LMFDB website.

The LMFDB's test suite exercises the utilities through the website; these
tests check that they work without it.  Most modules require Sage; without
it (as in .github/workflows/packaging.yml) only the others are tested.
"""
import importlib.util
import os
import pkgutil
import subprocess
import sys

import pytest

import lmfdb_utils
from lmfdb_utils import site as site_mod

HAVE_SAGE = importlib.util.find_spec("sage") is not None
needs_sage = pytest.mark.skipif(not HAVE_SAGE, reason="requires Sage")

# The modules that work without Sage
SAGE_FREE = {"color", "common_regex", "csrf", "datetime_utils", "knowledge", "lazy",
             "random_wrap", "schema", "sidebar", "site", "users", "web"}

MODULES = sorted(m.name for m in pkgutil.iter_modules(lmfdb_utils.__path__))


def run_py(code):
    # run in a directory unrelated to any checkout, so that the lmfdb
    # package of an LMFDB checkout cannot be imported by accident
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(lmfdb_utils.__file__)) + "/..",
    )


@pytest.mark.parametrize("module", MODULES)
def test_independent_of_the_lmfdb(module):
    # nothing in lmfdb-utils may import the LMFDB website: what it needs
    # from a website goes through lmfdb_utils.site
    if module not in SAGE_FREE and not HAVE_SAGE:
        pytest.skip("requires Sage")
    r = run_py(
        "import sys\n"
        "class Blocker:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name == 'lmfdb' or name.startswith('lmfdb.'):\n"
        "            raise ImportError('lmfdb_utils imported ' + name)\n"
        "sys.meta_path.insert(0, Blocker())\n"
        "import lmfdb_utils." + module + "\n"
    )
    assert r.returncode == 0, r.stderr


def test_no_lmfdb_imports_anywhere():
    # the same, for imports inside functions, which only run when called
    import re
    pattern = re.compile(r"^\s*(from|import)\s+lmfdb(\.|\s|$)", re.M)
    package_dir = os.path.dirname(os.path.abspath(lmfdb_utils.__file__))
    for path, dirs, files in os.walk(package_dir):
        for filename in files:
            if filename.endswith(".py"):
                with open(os.path.join(path, filename)) as F:
                    assert not pattern.search(F.read()), "%s imports from lmfdb" % filename


def test_templates_do_not_use_lmfdb_endpoints():
    # the templates may only link to the endpoints of lmfdb-utils (css,
    # static, knowledge.*, users.*) and to the site's index page
    import re
    endpoint = re.compile(r"""url_for\(\s*['"]([^'"]+)['"]""")
    allowed = {"css", "static", "index"}
    package_dir = os.path.dirname(os.path.abspath(lmfdb_utils.__file__))
    for path, dirs, files in os.walk(package_dir):
        for filename in files:
            if filename.endswith((".html", ".css")):
                with open(os.path.join(path, filename)) as F:
                    for name in endpoint.findall(F.read()):
                        assert (name in allowed or name.startswith((".", "knowledge.", "users."))), \
                            "%s links to %s" % (filename, name)


def test_package_and_site_are_light():
    # the website installs its Site when it is imported, so lmfdb_utils.site
    # must not import flask or sage
    r = run_py(
        "import sys\n"
        "import lmfdb_utils.site\n"
        "assert 'flask' not in sys.modules\n"
        "assert not any(m == 'sage' or m.startswith('sage.') for m in sys.modules)\n"
    )
    assert r.returncode == 0, r.stderr


@pytest.fixture
def site():
    # restore the installed site afterward
    old = site_mod.current_site()
    yield
    site_mod.set_current_site(old)


def test_default_site(site):
    site_mod.set_current_site(site_mod.Site())
    s = site_mod.current_site()
    assert s.knowl_title("any.knowl") is None
    assert s.knowl_create_url("any.knowl") is None
    assert s.all_knowls() == {}
    assert s.results_complete("table", {}, None) == (None, None, None)
    assert "longer than expected" in s.query_timeout_message()


@pytest.fixture
def app():
    flask = pytest.importorskip("flask")
    app = flask.Flask(__name__)
    app.secret_key = "test"
    with app.test_request_context("/"):
        yield app


@needs_sage
def test_display_knowl(site, app):
    from lmfdb_utils.web_display import display_knowl

    class KnowlSite(site_mod.Site):
        def knowl_title(self, kid):
            return {"nf.degree": "degree"}.get(kid)

        def knowl_create_url(self, kid):
            return "/create/" + kid

    site_mod.set_current_site(site_mod.Site())
    assert display_knowl("nf.degree", "Degree") == "Degree"
    site_mod.set_current_site(KnowlSite())
    assert display_knowl("nf.degree", "Degree") == '<a title="degree [nf.degree]" knowl="nf.degree" kwargs="">Degree</a>'
    assert 'href="/create/nf.missing"' in display_knowl("nf.missing", "Missing")


@needs_sage
def test_code_snippet_knowl(site, app):
    from lmfdb_utils.utilities import code_snippet_knowl
    D = {"filename": "site/main.py", "code": ["x = 1"], "lines": [3]}
    site_mod.set_current_site(site_mod.Site())
    assert "on Github" not in code_snippet_knowl(D)

    class SourceSite(site_mod.Site):
        def source_url(self, filename):
            return "https://example.org/" + filename

    site_mod.set_current_site(SourceSite())
    assert "https://example.org/site/main.py#L3" in code_snippet_knowl(D)


@needs_sage
def test_search_parsing(app):
    from lmfdb_utils.search_parsing import parse_ints, parse_floats
    info = {"degree": "2-4", "regulator": "0.5-1"}
    query = {}
    parse_ints(info, query, "degree")
    parse_floats(info, query, "regulator")
    assert query["degree"] == {"$gte": 2, "$lte": 4}
    assert set(query["regulator"]) == {"$gte", "$lte"}


def test_lazy_object():
    from lmfdb_utils.lazy import LazyObject
    created = []

    class Thing:
        value = 1

    def factory():
        created.append(1)
        return Thing()

    lazy = LazyObject(factory, "A thing")
    assert "created when first used" in repr(lazy)
    assert not created
    assert lazy.value == 1
    lazy.other = 2
    assert lazy.other == 2
    del lazy.other
    assert not hasattr(lazy, "other")
    assert created == [1]


def test_sidebar(site, app, tmp_path):
    from lmfdb_utils.sidebar import SideBar
    app.add_url_rule("/about", "about", lambda: "")
    sidebar_file = tmp_path / "sidebar.yaml"
    sidebar_file.write_text(
        "2second:\n  type: simple\n  heading:\n    title: Second\n  parts:\n"
        "    - title: About\n      url_for: about\n"
        "1first:\n  type: simple\n  heading:\n    title: First\n  parts:\n"
        "    - title: Later\n      status: future\n"
    )

    class SidebarSite(site_mod.Site):
        pass

    SidebarSite.sidebar_file = str(sidebar_file)
    site_mod.set_current_site(SidebarSite())
    with app.test_request_context("/"):
        data = SideBar().data
    assert [key for key, heading, value in data] == ["1first", "2second"]
    assert data[0][1] == "<h2>First</h2>\n"
    assert data[1][2]["parts"][0]["url"] == '<a href="/about">About</a>'
    assert 'class="future"' in data[0][2]["parts"][0]["url"]
    site_mod.set_current_site(site_mod.Site())
    assert SideBar().data == []


def test_color_schemes(site):
    from lmfdb_utils.color import ColorScheme, all_color_schemes

    class Mine(ColorScheme):
        code = 100
        col_main_d = "#123"
        col_main_dl = "#234"
        col_main = "#345"
        col_main_2 = "#456"
        col_main_l = "#567"
        col_main_lg = "#678"
        col_main_ld = "#789"
        col_main_ll = "#89a"

    class ColorSite(site_mod.Site):
        default_color = 100

        def color_schemes(self):
            return {**all_color_schemes, 100: Mine()}

    colors = ColorSite().color_schemes()[100].dict()
    assert colors["col_main"] == "#345"
    # the colors of the LMFDB's sections default to the main colors
    assert colors["lf_an_button_bkg"] == "#789"
    assert 100 not in all_color_schemes


@pytest.fixture
def web_app(site, tmp_path, monkeypatch):
    """
    A Flask application set up with init_app, for a site without a database:
    the user database is replaced by one that cannot log anyone in.
    """
    if not HAVE_SAGE:
        pytest.skip("requires Sage")
    flask = pytest.importorskip("flask")
    from lmfdb_utils import web
    import lmfdb_utils.users.main as users_main

    class NoUsers:
        def can_read_write_userdb(self):
            return False

    monkeypatch.setattr(users_main, "userdb", NoUsers())

    class TestSite(site_mod.Site):
        name = "Test Site"

    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "notify.min.js").write_text("// the site's own copy")
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "homepage.html").write_text(
        '{% extends "lmfdb_utils/layout.html" %}{% block footer %}OUR FOOTER{% endblock %}'
    )
    app = flask.Flask(
        "test_site",
        static_folder=str(tmp_path / "static"),
        template_folder=str(tmp_path / "templates"),
    )
    app.secret_key = "test"
    web.init_app(app, TestSite())
    app.add_url_rule("/", "index", lambda: flask.render_template("homepage.html", title="Home"))
    return app


def test_init_app(web_app):
    tc = web_app.test_client()
    # the style sheet, in the default color scheme
    response = tc.get("/style.css")
    assert response.status_code == 200
    assert response.headers["Content-type"].startswith("text/css")
    # static files: the package's, unless the site has its own
    assert b"knowl" in tc.get("/static/lmfdb.js").data
    assert tc.get("/static/notify.min.js").data == b"// the site's own copy"
    assert tc.get("/static/no_such_file.js").status_code == 404
    # a page, in the site's layout
    page = tc.get("/").get_data(as_text=True)
    assert "<title>Test Site - Home" in page
    assert "OUR FOOTER" in page
    assert 'src="/static/lmfdb.js"' in page
    # the knowledge and user pages are registered
    rules = {rule.endpoint for rule in web_app.url_map.iter_rules()}
    assert {"knowledge.show", "knowledge.edit", "users.info", "users.login", "css"} <= rules


def test_csrf(app):
    from flask import session
    from lmfdb_utils.csrf import csrf_token
    token = csrf_token()
    assert token == session["_csrf_token"] == csrf_token()


def test_version():
    assert lmfdb_utils.__version__
