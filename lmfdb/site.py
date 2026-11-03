"""
How the LMFDB describes itself to lmfdb-utils (see lmfdb_utils.site).

Importing the lmfdb package installs :class:`LMFDBSite`, so this module must
stay as light as lmfdb/__init__.py: everything else is imported when used.
"""

import os
import re

from lmfdb_utils.site import Site

# Where the pages annotated by <label>.top and <label>.bottom knowls are
ANNOTATION_URLS = [
    (re.compile(r'g2c\.(\d+\.[a-z]+\.\d+\.\d+)'), 'Genus2Curve/Q/{0}', 'Genus 2 curve {0}'),
    (re.compile(r'g2c\.(\d+\.[a-z]+)'), 'Genus2Curve/Q/{0}', 'Genus 2 isogeny class {0}'),
    (re.compile(r'gg\.(\d+)t(\d+)'), 'GaloisGroup/{0}t{1}', 'Galois group {0}T{1}'),
    (re.compile(r'lattice\.(.*)'), 'Lattice/{0}', 'Lattice {0}'),
    (re.compile(r'cmf\.(.*)'), 'ModularForm/GL2/Q/holomorphic/{0}', 'Newform {0}'),
    (re.compile(r'nf\.(.*)'), 'NumberField/{0}', 'Number field {0}'),
    (re.compile(r'ec\.q\.(.*)'), 'EllipticCurve/Q/{0}', 'Elliptic curve {0}'),
    (re.compile(r'ec\.(\d+\.\d+\.\d+\.\d+)-(\d+\.\d+)-([a-z]+)(\d+)'), 'EllipticCurve/{0}/{1}/{2}/{3}', 'Elliptic curve {0}-{1}-{2}{3}'),
    (re.compile(r'av\.fq\.(.*)'), 'Variety/Abelian/Fq/{0}', 'Abelian variety isogeny class {0}'),
    (re.compile(r'st_group\.(.*)'), 'SatoTateGroup/{0}', 'Sato-Tate group {0}'),
    (re.compile(r'belyi\.(.*)'), 'Belyi/{0}', 'Belyi Map {0}'),
    (re.compile(r'hecke_algebra\.(.*)'), 'ModularForm/GL2/Q/HeckeAlgebra/{0}', 'Hecke algebra {0}'),
    (re.compile(r'hecke_algebra_l_adic\.(.*)'), 'ModularForm/GL2/Q/HeckeAlgebra/{0}/2', 'l-adic Hecke algebra {0}'),
    (re.compile(r'gal\.modl\.(.*)'), 'Representation/Galois/ModL/{0}', 'Mod-l Galois representation {0}'),
    (re.compile(r'modlmf\.(.*)'), 'ModularForm/GL2/ModL/{0}', 'Mod-l modular form {0}'),
    (re.compile(r'group\.abstract\.(.*)'), 'Groups/Abstract/{0}', 'Abstract group {0}'),
]


class LMFDBSite(Site):
    name = "LMFDB"
    download_prefix = "lmfdb"
    meta_description = r'Welcome to the LMFDB, the database of L-functions, modular forms, and related objects. These pages are intended to be a modern handbook including tables, formulas, links, and references for L-functions and their underlying objects.'
    feedback_url = r"https://docs.google.com/spreadsheet/viewform?formkey=dDJXYXBleU1BMTFERFFIdjVXVmJqdlE6MQ"
    sidebar_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "homepage", "sidebar.yaml")
    source_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    knowl_annotation_urls = ANNOTATION_URLS
    external_definitions_knowl = "lmfdb.external_definitions"
    wiki_url = "https://wiki.l-functions.org/"
    registration_url = "http://beta.lmfdb.org"

    @property
    def db(self):
        from lmfdb import db
        return db

    @property
    def default_color(self):
        from lmfdb.config import current_configuration
        return current_configuration().get_color()

    def is_beta(self):
        from lmfdb.app import is_beta
        return is_beta()

    def url_prefix(self):
        from lmfdb.config import current_configuration
        return current_configuration().get_url_prefix()

    def source_url(self, filename):
        from lmfdb.app import is_beta, is_debug_mode, _url_source
        if is_debug_mode():
            branch = "main"
        elif is_beta():
            branch = "dev"
        else:
            branch = "web"
        return "%s%s/%s" % (_url_source, branch, filename)

    def results_complete(self, table, query, db, search_array=None):
        from lmfdb.utils.completeness import results_complete
        return results_complete(table, query, db, search_array)

    def query_timeout_message(self):
        from urllib.parse import urlparse
        from flask import request
        from lmfdb_utils.web import modify_url
        if urlparse(request.url).netloc == "beta.lmfdb.org":
            return (
                'The search query took longer than expected! Please try again later; if your search still times out, please help us improve by reporting this error <a href="%s" target=_blank>here</a>.'
                % self.feedback_url
            )
        beta_link = modify_url(scheme="https", netloc="beta.lmfdb.org")
        return (
            'The search query took longer than expected! The <a href="%s">same search</a> on beta.lmfdb.org may succeed (it is running on a server with faster disks).  You can also try again later; if your search still times out, please help us improve by reporting this error  <a href="%s" target=_blank>here</a>.'
            % (beta_link, self.feedback_url)
        )
