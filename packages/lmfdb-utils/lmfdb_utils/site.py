"""
What lmfdb_utils needs to know about the website using it.

A few utilities depend on things that only the website can provide: its
name, its knowls, which results it knows to be complete, and so on.  A
website describes itself by subclassing :class:`Site` and installing an
instance with :func:`set_current_site` when it starts, before handling
requests.  A site providing a database (:attr:`Site.db`) has knowls, stored
there (see :mod:`lmfdb_utils.knowledge`); the defaults otherwise describe a
site without knowls.

For example, the LMFDB installs ``lmfdb.site.LMFDBSite`` when the ``lmfdb``
package is imported.

This module must stay importable without flask or sage.  Most attributes have
defaults suitable for a new website; the ones a website normally sets are
``name``, ``download_prefix``, ``db`` and ``sidebar_file``.
"""


class Site:
    #: The name of the website, as it appears in text such as "downloaded
    #: from the LMFDB" (following "the") and in the titles of pages
    name = "database"

    #: The prefix of the names of downloaded files
    download_prefix = "download"

    #: The description of the website in the ``description`` meta tag
    meta_description = ""

    #: The address of a page where users can report problems, or None
    feedback_url = None

    #: The logo shown in the header, as a file name in the static folder
    #: (for example ``"images/logo.png"``), or None to show the name instead
    logo = None

    #: The YAML file describing the sidebar menu (see
    #: :mod:`lmfdb_utils.sidebar`), or None for an empty sidebar
    sidebar_file = None

    #: The code of the color scheme used when neither the request nor the
    #: user chooses one (see :mod:`lmfdb_utils.color`)
    default_color = 0

    #: The directory of the website's git checkout, searched for references
    #: to knowls (``git grep``); None if the code cannot be searched
    source_root = None

    #: The address that file names in the website's checkout are appended to
    #: to link to them, such as ``"https://github.com/<owner>/<repo>/blob/main/"``,
    #: or None (see :meth:`source_url`)
    source_url_base = None

    #: How annotation knowls (``<label>.top`` and ``<label>.bottom``) link to
    #: the page they annotate: a list of triples ``(regex, url, name)``, where
    #: ``url`` and ``name`` are formatted with the groups of the regex matching
    #: ``<label>``
    knowl_annotation_urls = ()

    #: The knowl displaying the external definitions of a term (see
    #: :func:`~lmfdb_utils.knowledge.knowl.knowl_definition`), or None
    external_definitions_knowl = None

    #: The base address of the wiki that ``[[topic]]`` links to in knowls, or
    #: None to leave ``[[topic]]`` alone
    wiki_url = None

    #: The address (scheme and host) used in the registration links created
    #: by administrators, or None for the address of the current request
    registration_url = None

    @property
    def db(self):
        """
        The database (a psycodict ``PostgresDatabase``) holding the website's
        data, knowls and users.
        """
        raise NotImplementedError("The website must provide its database (Site.db)")

    def is_beta(self):
        """
        Whether the website shows content still under review (such as knowls
        that have not been reviewed) and the links for logging in.  By default
        this is the case when Flask runs in debug mode, and outside the
        website (in scripts, which work with the latest versions of knowls).
        """
        from flask import current_app, has_app_context
        return current_app.debug if has_app_context() else True

    def url_prefix(self):
        """
        The prefix of the website's addresses, when it is not served from the
        root of its host (used by the javascript showing knowls).
        """
        return ""

    def color_schemes(self):
        """
        The color schemes users may choose, as a dictionary from codes to
        :class:`~lmfdb_utils.color.ColorScheme` instances.
        """
        from .color import all_color_schemes
        return all_color_schemes

    def has_database(self):
        """
        Whether the website provides a database (by overriding :attr:`db`);
        without one, it has no knowls.
        """
        return type(self).db is not Site.db

    def knowl_title(self, kid):
        """
        The title of the knowl with id ``kid``, or None if there is no such
        knowl.
        """
        if not self.has_database():
            return None
        from .knowledge.knowl import knowl_title
        return knowl_title(kid)

    def knowl_url(self, kid):
        """
        The path, on this website, of the page showing the knowl ``kid``
        (used in downloaded spreadsheets), or None.
        """
        if not self.has_database():
            return None
        from flask import url_for
        return url_for("knowledge.show", ID=kid)

    def knowl_create_url(self, kid):
        """
        The address of the page creating the missing knowl ``kid``, if the
        current user may create it, and None otherwise.
        """
        if not self.has_database():
            return None
        from flask import url_for
        from flask_login import current_user
        from .users.pwdmanager import userdb
        if current_user.is_authenticated and userdb.can_read_write_userdb():
            return url_for("knowledge.edit", ID=kid)

    def all_knowls(self):
        """
        A dictionary giving the title and content of every knowl, by id
        (used to describe the columns in downloaded files).
        """
        if not self.has_database():
            return {}
        from .knowledge.knowl import knowldb
        return {rec["id"]: (rec["title"], rec["content"]) for rec in knowldb.get_all_knowls(fields=["id", "title", "content"])}

    def source_url(self, filename):
        """
        The address of the file ``filename`` in the website's source code
        repository (used by
        :func:`~lmfdb_utils.utilities.code_snippet_knowl`), or None: by
        default, ``filename`` appended to :attr:`source_url_base`.
        """
        if self.source_url_base is None:
            return None
        return self.source_url_base + filename

    def results_complete(self, table, query, db, search_array=None):
        """
        Whether the database contains all objects satisfying a query.

        INPUT:

        - ``table`` -- string, the name of the table
        - ``query`` -- dictionary, the psycodict query
        - ``db`` -- the database
        - ``search_array`` -- the search array of the search, or None

        OUTPUT:

        A triple ``(complete, reason, caveat)``: ``complete`` is True if
        every object satisfying the query is included in the results, False
        if objects may be missing, and None if unknown; ``reason`` is a
        string that can follow "The <name> contains all" when ``complete``;
        ``caveat`` is a string qualifying the answer, or None.
        """
        return None, None, None

    def query_timeout_message(self):
        """
        The message (HTML) shown when a search takes too long and is
        cancelled.
        """
        return "The search query took longer than expected!  Please try again later."


_current_site = Site()


def current_site():
    """
    The :class:`Site` installed with :func:`set_current_site` (by default,
    one describing a site without knowls).
    """
    return _current_site


def set_current_site(site):
    """
    Install ``site``, an instance of a subclass of :class:`Site`, as the
    website using these utilities.
    """
    global _current_site
    _current_site = site
