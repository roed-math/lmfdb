# lmfdb-utils

Utilities for running a website like the [L-functions and modular forms database](https://www.lmfdb.org) (LMFDB): a [Flask](https://flask.palletsprojects.com) site presenting mathematical objects stored in a PostgreSQL database accessed through [psycodict](https://github.com/roed314/psycodict).  This package is built from the [LMFDB repository](https://github.com/LMFDB/lmfdb), where the LMFDB website uses it, so other websites share the LMFDB's code rather than copies of it.

## Install

Most of the modules require [SageMath](https://www.sagemath.org), which pip cannot install, so install this package into Sage's Python:

```
sage -pip install lmfdb-utils
```

## Contents

- `web`: `init_app(app, site)` sets up a Flask application with everything below: the page layout and the templates and static files of the utilities, the style sheet, the knowledge database and user accounts (see "Setting up a website");
- `search_boxes`: the boxes of search forms (`SearchArray`, `TextBox`, `SelectBox`, ...) and the sorting and column controls;
- `search_parsing`: parsing what users type into search boxes into psycodict queries (`parse_ints`, `parse_floats`, `parse_bracketed_posints`, ..., and the `search_parser` decorator for writing new parsers);
- `search_wrapper`: `search_wrap`, `count_wrap`, `embed_wrap` and `yield_wrap`, which turn a function filling in a query into a search results page (with pagination, sorting, random results, downloads and diagram views);
- `search_columns`: the columns of search results tables, and how they are displayed and downloaded;
- `downloader`: `Downloader`, for downloading search results and single objects in Sage, Magma, Pari/GP, GAP, Oscar, CSV and text formats;
- `display_stats`: `StatsDisplay`, for statistics pages built from psycodict's statistics tables;
- `knowledge`: knowls, the short definitions that appear when clicked, with the pages for showing, editing, reviewing and searching them (`/knowledge`);
- `users`: user accounts, logging in, and registration by invitation (`/users`);
- `schema`: creating the tables of the knowls and user accounts in a new database (`create_tables`, `grant_website_access`, `add_user`);
- `sidebar`: the sidebar menu, read from a YAML file;
- `web_display` and `utilities`: displaying mathematical objects (`web_latex`, `raw_typeset`, `bigint_knowl`, `display_knowl`, ...), flashing messages (`flash_error`, ...), pagination and other helpers;
- `color`: the color schemes of the style sheet;
- `place_code`: `CodeSnippet`, for showing code in several computer algebra systems;
- `csrf`, `random_wrap`, `datetime_utils`, `common_regex`: small helpers.

## Setting up a website

A website describes itself by subclassing `lmfdb_utils.site.Site` and passing an instance to `init_app` when it creates its Flask application:

```python
from flask import Flask, render_template
from lmfdb_utils.site import Site
from lmfdb_utils.web import init_app

class MySite(Site):
    name = "Diophantine Library"  # in titles, and in "downloaded from the Diophantine Library"
    download_prefix = "dl"
    sidebar_file = "sidebar.yaml"

    @property
    def db(self):
        ...  # the psycodict PostgresDatabase holding the data, knowls and users

app = Flask(__name__)
app.secret_key = ...
init_app(app, MySite())

@app.route("/")
def index():
    return render_template("homepage.html", title="Welcome")
```

See the docstrings in `lmfdb_utils/site.py` for the other attributes (logo, color scheme, feedback page, ...) and methods, and `lmfdb/site.py` in the LMFDB repository for the LMFDB's implementation.  The [LMFDB website template](https://github.com/LMFDB/lmfdb-template) is a complete example, with instructions for setting up the database.

Pages extend `homepage.html`, which fills in `lmfdb_utils/layout.html` (header, sidebar, properties box, content and footer), itself extending `base.html` and `lmfdb_utils/base.html` (the head of the page, its scripts and the knowl macros).  A website changes them by putting a template of the same name in its own `templates` folder, which takes precedence over the package's: for example a `homepage.html` that extends `lmfdb_utils/layout.html` and fills in its `logo`, `undertopright` and `footer` blocks, or a `base.html` that extends `lmfdb_utils/base.html` and fills in `head_early`, `head_late` (analytics, its own style sheet) or `katex_macros`.  Static files work the same way: `/static/<file>` is the website's own file if it has one, and the package's otherwise.

The colors of the style sheet come from a color scheme (`lmfdb_utils.color.ColorScheme`): a website defines its own as a subclass setting the main colors (`col_main`, `col_main_d`, ...), and returns it from `Site.color_schemes`, choosing it with `Site.default_color`.

The knowls and users are stored in the website's database, in the tables created by `lmfdb_utils.schema.create_tables`.  A website whose database role can only read them shows knowls but lets nobody log in or edit them (as on www.lmfdb.org).

## Development

This package lives in `packages/lmfdb-utils` in the [LMFDB repository](https://github.com/LMFDB/lmfdb); an LMFDB checkout installs it in editable mode (`sage -pip install -r requirements.txt`).  Its modules must not import anything from the `lmfdb` package: what they need from the website goes through `lmfdb_utils.site`.  The tests in `packages/lmfdb-utils/tests` check this, and the LMFDB's own test suite exercises the utilities through the website.
