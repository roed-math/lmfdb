# Changes to lmfdb-utils

lmfdb-utils follows semantic versioning: websites using it can update within
a minor version (0.1.x) without changes; a new minor version (before 1.0) or
major version may need changes to them, which are described here.

## Unreleased (0.1.0)

First release, built from the LMFDB repository:

- the search, results, downloads and statistics utilities of the LMFDB
  (`search_boxes`, `search_parsing`, `search_wrapper`, `search_columns`,
  `downloader`, `display_stats`, `web_display`, `utilities`, ...);
- `site.Site`, through which a website describes itself to the utilities;
- `web.init_app`, setting up a Flask application with the page layout
  (`lmfdb_utils/base.html`, `lmfdb_utils/layout.html`), the templates and
  static files the utilities use, the style sheet and its color schemes, the
  sidebar, knowls (`knowledge`) and user accounts (`users`);
- `schema`, creating the tables of knowls and user accounts.
