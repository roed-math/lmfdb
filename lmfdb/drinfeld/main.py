import re

from flask import render_template, url_for, request, redirect, abort
from sage.all import ZZ, GF, PolynomialRing, conway_polynomial

from lmfdb import db
from lmfdb.api import datapage
from lmfdb.utils import (
    SearchArray,
    TextBox,
    YesNoBox,
    CountBox,
    StatsDisplay,
    Downloader,
    comma,
    display_knowl,
    flash_error,
    parse_bool,
    parse_ints,
    proportioners,
    redirect_no_cache,
    search_wrap,
    to_dict,
    totaler,
)
from lmfdb.utils.search_columns import SearchColumns, MathCol, CheckCol, LinkCol, ProcessedCol
from lmfdb.utils.search_parsing import search_parser, SearchParsingError
from lmfdb.drinfeld import drinfeld_page
from lmfdb.drinfeld.web_drinfeld import (
    ISOG_LABEL_RE,
    MODULE_LABEL_RE,
    WebDrinfeldIsogenyClass,
    WebDrinfeldModule,
    get_bread,
    module_points_tex,
    sage_tex,
    url_for_label,
)


def learnmore_list():
    return [("Source and acknowledgments", url_for(".how_computed_page")),
            ("Completeness of the data", url_for(".completeness_page")),
            ("Reliability of the data", url_for(".reliability_page")),
            ("Drinfeld module labels", url_for(".labels_page"))]


def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


@drinfeld_page.route("/")
def index():
    return redirect(url_for(".index_Fq", **request.args))


@drinfeld_page.route("/Fq/")
def index_Fq():
    info = to_dict(request.args, search_array=DrinfeldSearchArray())
    if request.args:
        if info.get("search_type", info.get("hst")) == "Modules":
            return drinfeld_module_search(info)
        return drinfeld_isog_search(info)
    info["stats"] = DrinfeldStats()
    # column_counts keys follow the sorted column names
    info["fields"] = sorted((q, n) for (n, q) in db.drinfeld_isog.stats.column_counts(["n", "q"]))
    info["ranks"] = sorted({r for (q, r) in db.drinfeld_isog.stats.column_counts(["q", "rank"])})
    return render_template(
        "drinfeld_browse.html",
        info=info,
        title="Drinfeld modules over finite fields",
        bread=get_bread(),
        learnmore=learnmore_list(),
    )


@drinfeld_page.route("/Fq/random")
@redirect_no_cache
def random_isogeny_class():
    return url_for_label(db.drinfeld_isog.random())


@drinfeld_page.route("/Fq/<label>")
def by_label(label):
    if ISOG_LABEL_RE.fullmatch(label):
        obj, template, noun = WebDrinfeldIsogenyClass(label), "drinfeld_isog.html", "isogeny class"
    elif MODULE_LABEL_RE.fullmatch(label):
        obj, template, noun = WebDrinfeldModule(label), "drinfeld_module.html", "Drinfeld module"
    else:
        flash_error("%s is not a valid label for a Drinfeld module or isogeny class", label)
        return redirect(url_for(".index_Fq"))
    if obj.is_null():
        flash_error("There is no %s %s in the database", noun, label)
        return redirect(url_for(".index_Fq"))
    return render_template(
        template,
        obj=obj,
        properties=obj.properties,
        friends=obj.friends,
        downloads=obj.downloads,
        bread=obj.bread,
        title=obj.title,
        learnmore=learnmore_list(),
        KNOWL_ID="drinfeld.%s" % label,
    )


def drinfeld_jump(info):
    label = info.get("jump", "").strip()
    if ISOG_LABEL_RE.fullmatch(label) or MODULE_LABEL_RE.fullmatch(label):
        return redirect(url_for_label(label))
    flash_error("%s is not a valid label for a Drinfeld module or isogeny class", label)
    return redirect(url_for(".index_Fq"))


CHAR_POLY_RE = re.compile(r"[0-9Tb+\-*^() ]+")


@search_parser
def parse_char_poly(inp, query, qfield):
    """
    The A-characteristic P, entered as a monic polynomial in T over F_q (with b
    the Conway generator of F_q), stored as its list of encoded coefficients.
    """
    # Exponents are capped since the string is evaluated by Sage
    if not CHAR_POLY_RE.fullmatch(inp) or re.search(r"\^(?!\s*\d{1,3}(?!\d))", inp):
        raise SearchParsingError("It must be a polynomial in T, such as T^2 + T + 1")
    q = query.get("q")
    if not isinstance(q, int) or not ZZ(q).is_prime_power():
        raise SearchParsingError("To search on the characteristic, also give a single prime power q")
    p, k = ZZ(q).is_prime_power(get_data=True)
    Fq = GF(p) if k == 1 else GF(q, "b", modulus=conway_polynomial(p, k))
    try:
        P = PolynomialRing(Fq, "T")(inp)
    except (TypeError, ValueError, SyntaxError, NameError):
        raise SearchParsingError("Unable to read it as a polynomial in T over F_%s" % q)
    if not P.is_monic():
        raise SearchParsingError("It must be monic")
    query[qfield] = [sum(int(c) * p**i for i, c in enumerate(a.polynomial().list())) if k > 1 else int(a)
                     for a in P.list()]


def common_parse(info, query):
    parse_ints(info, query, "q")
    parse_ints(info, query, "n")
    parse_ints(info, query, "rank")
    parse_ints(info, query, "p", name="characteristic of F_q")
    parse_char_poly(info, query, "char_poly", name="A-characteristic")


isog_columns = SearchColumns([
    LinkCol("label", "drinfeld.label", "Label", url_for_label),
    MathCol("q", "drinfeld.q", "$q$"),
    MathCol("n", "drinfeld.base_field", "$n$"),
    MathCol("rank", "drinfeld.rank", "Rank"),
    ProcessedCol("char_poly_str", "drinfeld.a_characteristic", "Characteristic",
                 lambda s: "$%s$" % sage_tex(s), align="center"),
    MathCol("m", "drinfeld.a_characteristic", "$m$", default=False),
    ProcessedCol("frob_poly_str", "drinfeld.frobenius_charpoly", "Frobenius polynomial",
                 lambda s: "$%s$" % sage_tex(s)),
    MathCol("height", "drinfeld.height", "Height"),
    CheckCol("commutative_endomorphisms", "drinfeld.endomorphism_algebra", "Comm. End"),
    MathCol("geometric_extension_degree", "drinfeld.geometric_extension_degree", "Geom. ext. degree", default=False),
    MathCol("size", "drinfeld.isogeny_class_size", "Isom. classes"),
    ProcessedCol("weighted_size_Q", "drinfeld.isogeny_class_size", "Weighted size",
                 lambda s: "$%s$" % s, align="center", default=False),
])


@search_wrap(
    table=db.drinfeld_isog,
    title="Drinfeld module isogeny class search results",
    err_title="Drinfeld module search input error",
    shortcuts={"jump": drinfeld_jump, "download": Downloader(db.drinfeld_isog)},
    columns=isog_columns,
    bread=lambda: get_bread("Search results"),
    url_for_label=url_for_label,
)
def drinfeld_isog_search(info, query):
    common_parse(info, query)
    parse_ints(info, query, "m")
    parse_ints(info, query, "height")
    parse_ints(info, query, "geometric_extension_degree")
    parse_ints(info, query, "size")
    parse_bool(info, query, "commutative_endomorphisms")


module_columns = SearchColumns([
    LinkCol("label", "drinfeld.label", "Label", url_for_label),
    LinkCol("isogeny_label", "drinfeld.isogeny_class", "Isogeny class", url_for_label),
    MathCol("q", "drinfeld.q", "$q$"),
    MathCol("n", "drinfeld.base_field", "$n$"),
    MathCol("rank", "drinfeld.rank", "Rank"),
    ProcessedCol("char_poly_str", "drinfeld.a_characteristic", "Characteristic",
                 lambda s: "$%s$" % sage_tex(s), align="center"),
    ProcessedCol("ore_poly_str", "drinfeld.definition", r"$\phi_T$", lambda s: "$%s$" % sage_tex(s)),
    MathCol("automorphisms", "drinfeld.automorphism_group", r"$\#\mathrm{Aut}$"),
    ProcessedCol("module_points_str", "drinfeld.rational_points", r"$\phi(L)$",
                 lambda s: "$%s$" % module_points_tex(s), default=False),
])


@search_wrap(
    table=db.drinfeld_modules,
    title="Drinfeld module search results",
    err_title="Drinfeld module search input error",
    shortcuts={"jump": drinfeld_jump, "download": Downloader(db.drinfeld_modules)},
    columns=module_columns,
    bread=lambda: get_bread("Search results"),
    url_for_label=url_for_label,
)
def drinfeld_module_search(info, query):
    common_parse(info, query)
    parse_ints(info, query, "automorphisms")


class DrinfeldSearchArray(SearchArray):
    noun = "isogeny class"
    plural_noun = "isogeny classes"
    jump_example = "2.3.2.3_9.1"
    jump_egspan = "e.g. 2.3.2.3_9 (isogeny class) or 2.3.2.3_9.1 (Drinfeld module)"
    jump_prompt = "Label"
    jump_knowl = "drinfeld.search_input"

    _isog_sort = ["q", "n", "rank", ("m", -1), "char_poly", "frob_poly"]
    _module_sort = ["q", "n", "rank", "char_poly", "isogeny_label", "ore_poly"]
    sorts = {
        "": [
            ("", "base field", _isog_sort),
            ("rank", "rank", ["rank"] + _isog_sort),
            ("size", "isomorphism classes", [("size", -1)] + _isog_sort),
            ("height", "height", ["height"] + _isog_sort),
        ],
        "Modules": [
            ("", "base field", _module_sort),
            ("rank", "rank", ["rank"] + _module_sort),
            ("automorphisms", "automorphisms", [("automorphisms", -1)] + _module_sort),
        ],
    }

    def __init__(self):
        q = TextBox(name="q", knowl="drinfeld.q", label="$q$", example="3", example_span="3 or 2-5")
        n = TextBox(name="n", knowl="drinfeld.base_field", label=r"$n = [L : \F_q]$",
                    example="2", example_span="1 or 1-3")
        rank = TextBox(name="rank", knowl="drinfeld.rank", label="Rank", example="2", example_span="2 or 1-3")
        p = TextBox(name="p", knowl="drinfeld.q", label="Characteristic of $\\F_q$", example="2")
        char_poly = TextBox(name="char_poly", knowl="drinfeld.a_characteristic", label="Characteristic",
                            example="T^2 + T + 1", example_span="T + b, with $q$ given")
        m = TextBox(name="m", knowl="drinfeld.a_characteristic", label="$m = n/\\deg P$", example="1")
        height = TextBox(name="height", knowl="drinfeld.height", label="Height", example="1", example_span="1 or 2-3")
        commutative = YesNoBox(name="commutative_endomorphisms", knowl="drinfeld.endomorphism_algebra",
                               label="Commutative $\\mathrm{End}^0$", example_col=True)
        geom = TextBox(name="geometric_extension_degree", knowl="drinfeld.geometric_extension_degree",
                       label="Geometric extension degree", example="2", example_span="1 or 2-6")
        size = TextBox(name="size", knowl="drinfeld.isogeny_class_size", label="Isomorphism classes",
                       example="2", example_span="1 or 2-10")
        aut = TextBox(name="automorphisms", knowl="drinfeld.automorphism_group",
                      label="Automorphisms", example="3", example_span="1 or 3-8")
        count = CountBox()

        self.browse_array = [
            [q, n],
            [rank, p],
            [char_poly, m],
            [height, commutative],
            [geom, size],
            [aut, count],
        ]
        self.isog_refine_array = [
            [q, n, rank, p],
            [char_poly, m, height, commutative],
            [geom, size],
        ]
        self.module_refine_array = [
            [q, n, rank, p],
            [char_poly, aut],
        ]

    def main_array(self, info):
        if info is None:
            return self.browse_array
        if self._st(info) == "Modules":
            return self.module_refine_array
        return self.isog_refine_array

    def search_types(self, info):
        if info is None:
            return [("List", "List of isogeny classes"),
                    ("Modules", "List of Drinfeld modules"),
                    ("Random", "Random isogeny class")]
        return self._search_again(info, [("List", "Isogeny classes"),
                                         ("Modules", "Drinfeld modules"),
                                         ("Random", "Random isogeny class")])


class DrinfeldStats(StatsDisplay):
    table = db.drinfeld_isog
    baseurl_func = ".index_Fq"
    knowls = {
        "q": "drinfeld.q",
        "n": "drinfeld.base_field",
        "rank": "drinfeld.rank",
        "height": "drinfeld.height",
        "geometric_extension_degree": "drinfeld.geometric_extension_degree",
    }
    short_display = {"geometric_extension_degree": "geometric extension degree"}
    top_titles = {
        "q": "size $q$ of the constant field",
        "n": "degree $n$ of the base field",
        "rank": "rank",
        "height": "height",
        "geometric_extension_degree": "geometric extension degree",
    }
    stat_list = [
        {"cols": ["q", "n"], "totaler": totaler()},
        {"cols": ["rank", "q"], "totaler": totaler()},
        {"cols": ["rank", "height"], "proportioner": proportioners.per_row_total, "totaler": totaler()},
        {"cols": ["rank", "geometric_extension_degree"], "proportioner": proportioners.per_row_total,
         "totaler": totaler()},
    ]

    def __init__(self):
        self.nisog = comma(db.drinfeld_isog.count())
        self.nmodules = comma(db.drinfeld_modules.count())
        self.max_rank = db.drinfeld_isog.max("rank")
        self.max_q = db.drinfeld_isog.max("q")
        self.max_n = db.drinfeld_isog.max("n")

    @property
    def short_summary(self):
        return self.summary + r' You can <a href="%s">browse further statistics</a>.' % url_for(".statistics")

    @property
    def summary(self):
        return (
            r"The database currently contains %s %s of %s over finite fields $L = \F_{q^n}$, "
            r"falling into %s %s, for rank $r \le %s$, $q \le %s$ and $n \le %s$."
            % (self.nmodules, display_knowl("drinfeld.isomorphism", "isomorphism classes"),
               display_knowl("drinfeld.definition", r"Drinfeld $\F_q[T]$-modules"),
               self.nisog, display_knowl("drinfeld.isogeny_class", "isogeny classes"),
               self.max_rank, self.max_q, self.max_n))


@drinfeld_page.route("/Fq/stats")
def statistics():
    title = "Drinfeld modules over finite fields: statistics"
    return render_template("display_stats.html", info=DrinfeldStats(), title=title,
                           bread=get_bread("Statistics"), learnmore=learnmore_list())


@drinfeld_page.route("/Fq/Source")
def how_computed_page():
    t = "Source and acknowledgments for Drinfeld module data"
    return render_template("multi.html",
                           kids=["rcs.source.drinfeld", "rcs.ack.drinfeld", "rcs.cite.drinfeld"],
                           title=t, bread=get_bread("Source"), learnmore=learnmore_list_remove("Source"))


@drinfeld_page.route("/Fq/Completeness")
def completeness_page():
    t = "Completeness of Drinfeld module data"
    return render_template("single.html", kid="rcs.cande.drinfeld",
                           title=t, bread=get_bread("Completeness"), learnmore=learnmore_list_remove("Completeness"))


@drinfeld_page.route("/Fq/Reliability")
def reliability_page():
    t = "Reliability of Drinfeld module data"
    return render_template("single.html", kid="rcs.rigor.drinfeld",
                           title=t, bread=get_bread("Reliability"), learnmore=learnmore_list_remove("Reliability"))


@drinfeld_page.route("/Fq/Labels")
def labels_page():
    t = "Labels for Drinfeld modules"
    return render_template("single.html", kid="drinfeld.label",
                           title=t, bread=get_bread("Labels"), learnmore=learnmore_list_remove("labels"))


@drinfeld_page.route("/Fq/data/<label>")
def drinfeld_data(label):
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    if ISOG_LABEL_RE.fullmatch(label):
        return datapage([label, label], ["drinfeld_isog", "drinfeld_modules"],
                        label_cols=["label", "isogeny_label"],
                        title="Drinfeld module isogeny class data - %s" % label, bread=bread)
    elif MODULE_LABEL_RE.fullmatch(label):
        return datapage(label, "drinfeld_modules", title="Drinfeld module data - %s" % label, bread=bread)
    return abort(404, "Invalid label %s" % label)
