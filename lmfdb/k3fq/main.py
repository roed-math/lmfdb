import re

from flask import abort, render_template, url_for, request, redirect

from sage.all import ZZ

from lmfdb.utils import (
    to_dict, flash_error, integer_options, display_knowl, coeff_to_poly,
    SearchArray, TextBox, SelectBox, YesNoBox, YesNoMaybeBox, CountBox,
    parse_ints, parse_bool, parse_bool_unknown, parse_restricted,
    search_wrap, count_wrap, redirect_no_cache,
)
from lmfdb.utils.search_parsing import search_parser, parse_range2, collapse_ors, LIST_RE
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, SearchCol, MathCol, ProcessedLinkCol, ProcessedCol, CheckCol
from lmfdb.api import datapage
from lmfdb.abvar.fq.search_parsing import parse_nf_string
from psycodict.utils import SearchParsingError

from lmfdb import db
from . import k3fq_page
from .web_k3fq import (
    WebK3Fq, isog_table, table_exists, validate_label, poly_to_label, lpoly_to_poly,
    realizable_display, label_wbr, LABEL_RE, ISOG_TABLE, LATTICE_TABLE, DEGREE,
)
from .stats import K3FqStats
from .download import K3Fq_download


#########################
#    Top level
#########################

def get_bread(*breads):
    bc = [
        ("Motives", url_for("motives")),
        ("K3 type", url_for(".index")),
        (r"$\F_q$", url_for(".index")),
    ]
    bc.extend(breads)
    return bc


def learnmore_list():
    return [
        ("Source and acknowledgments", url_for(".how_computed_page")),
        ("Completeness of the data", url_for(".completeness_page")),
        ("Reliability of the data", url_for(".reliability_page")),
        ("Labeling convention", url_for(".labels_page")),
    ]


# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


# Pages that only display knowls, and so work before the data is available
STATIC_ENDPOINTS = ["k3fq.how_computed_page", "k3fq.completeness_page",
                    "k3fq.reliability_page", "k3fq.labels_page", "k3fq.static"]


@k3fq_page.before_request
def require_table():
    # The tables for this section are not yet in every copy of the database
    if request.endpoint not in STATIC_ENDPOINTS and not table_exists():
        return abort(404, "The data on motives of K3 type over finite fields is not available in this database.")


#########################
#    Downloads
#########################

@k3fq_page.route("/download_all/<label>")
def download_all(label):
    return K3Fq_download().download_all(label)


@k3fq_page.route("/data/<label>")
def K3_data(label):
    if not LABEL_RE.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    bread = get_bread((label, url_for_label(label)), ("Data", " "))
    tables = [ISOG_TABLE]
    labels = [label]
    label_cols = ["label"]
    if table_exists(LATTICE_TABLE):
        tables.append(LATTICE_TABLE)
        labels.append(label)
        label_cols.append("isog_label")
    return datapage(labels, tables, title=f"Motive of K3 type data - {label}", bread=bread, label_cols=label_cols)


#########################
#  Search/navigate
#########################

@k3fq_page.route("/")
def index():
    info = to_dict(request.args, search_array=K3FqSearchArray())
    if request.args:
        # hidden_search_type for prev/next buttons
        info["search_type"] = search_type = info.get("search_type", info.get("hst", ""))
        if search_type == "Counts":
            return k3fq_count(info)
        elif search_type in ["List", "", "Random"]:
            return k3fq_search(info)
        else:
            flash_error("Invalid search type; if you did not enter it in the URL please report")
    return k3fq_browse(info)


def url_for_label(label):
    label = label.replace(" ", "")
    try:
        validate_label(label)
    except ValueError as err:
        flash_error("%s is not a valid label: %s.", label, str(err))
        return url_for(".index")
    return url_for(".by_label", label=label)


@k3fq_page.route("/<label>")
def by_label(label):
    try:
        validate_label(label)
    except ValueError as err:
        flash_error("%s is not a valid label: %s.", label, str(err))
        return redirect(url_for(".index"))
    try:
        cl = WebK3Fq.by_label(label)
    except ValueError:
        return abort(404, "Class %s is not in the database." % label)
    downloads = [
        ("All stored data to text", url_for(".download_all", label=label)),
        ("Underlying data", url_for(".K3_data", label=label)),
    ]
    return render_template(
        "k3fq-show.html",
        properties=cl.properties(),
        friends=cl.friends(),
        downloads=downloads,
        title="Motive of K3 type %s over $%s$" % (label, cl.field()),
        bread=get_bread((label, " ")),
        cl=cl,
        learnmore=learnmore_list(),
        KNOWL_ID="k3.fq.%s" % label,
    )


def jump(info):
    jump_box = info["jump"].strip()  # only called when this present
    try:
        validate_label(jump_box)
    except ValueError:
        # Also accept polynomials, either P(T) (constant term q) or L(T) (constant term 1)
        try:
            if jump_box.startswith("["):
                # a list of coefficients, constant term first
                coeffs = [ZZ(c) for c in jump_box.strip("[]").split(",")]
            else:
                poly = coeff_to_poly(jump_box)
                coeffs = poly.list()
                if not all(c in ZZ for c in coeffs):
                    raise ValueError
                coeffs = [ZZ(c) for c in coeffs]
            if len(coeffs) != DEGREE + 1:
                raise ValueError
            if coeffs[0] == 1:
                coeffs = lpoly_to_poly(coeffs)
            jump_box = poly_to_label(coeffs)
        except Exception:
            flash_error("%s is not valid input.  Expected a label or a polynomial P(T) or L(T) of degree 22.", jump_box)
            return redirect(url_for(".index"))
    return redirect(url_for(".by_label", label=jump_box))


#########################
#  Search parsing
#########################

INITIAL_COEFFS_RE = re.compile(r"^\[?-?\d+(,-?\d+)*\]?$")
SIGNED_RANGE_RE = re.compile(r"^-?\d+(--?\d+|-)?(,-?\d+(--?\d+|-)?)*$")
INFINITY_STRINGS = ["inf", "infinity", "oo", "∞"]


@search_parser(clean_info=True)
def parse_initial_coefficients(inp, query, qfield, q=None):
    """
    Search on the initial coefficients a_1, a_2, ... of P(T), using the
    poly_str column (whose first entry is a_0 = q).
    """
    if not INITIAL_COEFFS_RE.fullmatch(inp):
        raise SearchParsingError("It must be a list of integers, such as [-1, 3, 5], giving the initial coefficients a_1, a_2, ... of P(T)")
    coeffs = [int(c) for c in inp.strip("[]").split(",")]
    if len(coeffs) > DEGREE:
        raise SearchParsingError("P(T) has only 22 coefficients after the constant term")
    tail = " ".join(str(c) for c in coeffs) + " "
    if isinstance(q, int):
        query[qfield] = {"$startswith": "%s %s" % (q, tail)}
    else:
        query[qfield] = {"$regex": "^[0-9]+ " + tail}


@search_parser(clean_info=True, prep_ranges=True)
def parse_signed_range(inp, query, qfield):
    """
    Like parse_ints, but allows negative integers (ranges like -5-3 or -10--2).
    """
    if not SIGNED_RANGE_RE.fullmatch(inp):
        raise SearchParsingError("It needs to be an integer (such as -25), a range of integers (such as -10-10 or -10..10), or a comma-separated list of these.")
    collapse_ors(parse_range2(inp, qfield), query)


@search_parser(clean_info=True, prep_ranges=True)
def parse_height(inp, query, qfield):
    """
    Like parse_ints, but also allows "inf" for the supersingular case (where the height is null).
    """
    parts = []
    for part in inp.split(","):
        if part.lower() in INFINITY_STRINGS:
            parts.append({qfield: None})
        elif LIST_RE.fullmatch(part):
            key, val = parse_range2(part, qfield)
            parts.append({key: val})
        else:
            raise SearchParsingError("It needs to be a positive integer (such as 2), a range (such as 2-5), inf (for supersingular classes), or a comma separated list of these")
    if len(parts) == 1:
        query.update(parts[0])
    else:
        collapse_ors(["$or", parts], query)


@search_parser(clean_info=True)
def parse_k3_label(inp, query, qfield):
    try:
        validate_label(inp)
    except ValueError as err:
        raise SearchParsingError(str(err))
    query[qfield] = inp


@search_parser(clean_info=True, error_is_safe=True)
def parse_galgrp(inp, query, qfield):
    """
    Search for classes where the Galois group of some factor of the transcendental
    part is one of the given groups.
    """
    from lmfdb.galois_groups.transitive_group import complete_group_codes
    try:
        gcs, _ = complete_group_codes(inp)
    except NameError:
        raise SearchParsingError("It needs to be a <a title='Galois group labels' knowl='nf.galois_group.name'>group label</a>, such as C4 or 4T1, or a comma separated list of such labels")
    query[qfield] = {"$overlaps": ["%sT%s" % (n, t) for n, t in gcs]}


NEWTON_OPTIONS = {
    "ordinary": {"is_ordinary": True},
    "supersingular": {"is_supersingular": True},
    "neither": {"is_ordinary": False, "is_supersingular": False},
    "not_ordinary": {"is_ordinary": False},
    "not_supersingular": {"is_supersingular": False},
}

BOOL_COLUMNS = ["ej_condition", "has_nonnegative_counts", "has_count_growth", "is_pointless",
                "is_primitive", "transcendental_irreducible", "has_k3_newton_polygon"]

REALIZABLE_COLUMNS = ["realizable_k3", "realizable_nck3", "realizable_cubic", "realizable_nccubic",
                      "realizable_gm", "realizable_ncgm", "realizable_verra", "realizable_ncverra",
                      "realizable_kummer"]


def common_parse(info, query):
    parse_ints(info, query, "q", name="base field cardinality")
    parse_ints(info, query, "p", name="base field characteristic")
    parse_ints(info, query, "r", name="degree of the base field")
    parse_restricted(info, query, "sign", allowed=["1", "-1"], process=int)
    parse_ints(info, query, "picard_rank", name="Picard rank")
    parse_ints(info, query, "geometric_picard_rank", name="geometric Picard rank")
    parse_height(info, query, "height", name="height")
    newton = info.get("newton")
    if newton:
        if newton not in NEWTON_OPTIONS:
            flash_error("%s is not a valid input for Newton polygon.", newton)
            raise SearchParsingError("Invalid Newton polygon type")
        query.update(NEWTON_OPTIONS[newton])
    parse_ints(info, query, "angle_rank")
    parse_ints(info, query, "angle_corank")
    parse_ints(info, query, "newton_elevation")
    parse_ints(info, query, "geometric_extension_degree", name="geometric extension degree")
    q = query.get("q")
    parse_initial_coefficients(info, query, "initial_coefficients", qfield="poly_str", q=q if isinstance(q, int) else None)
    parse_signed_range(info, query, "k3_count", name="point count")
    parse_ints(info, query, "artin_tate_value", name="Artin-Tate value")
    parse_signed_range(info, query, "ns_disc_class", name="NS discriminant class")
    for col in BOOL_COLUMNS:
        parse_bool(info, query, col)
    for col in REALIZABLE_COLUMNS:
        parse_bool_unknown(info, query, col)
    parse_ints(info, query, "twist_count", name="number of twists")
    parse_ints(info, query, "max_twist_degree", name="maximum twist degree")
    parse_ints(info, query, "num_lattices", name="number of lattices")
    parse_k3_label(info, query, "geometric_class", name="geometric class")
    parse_nf_string(info, query, "number_field", qfield="number_fields")
    parse_galgrp(info, query, "galois_group", qfield="galois_groups")


class K3FqSearchArray(SearchArray):
    sorts = [("", "base field", ["q", "poly"]),
             ("p", "characteristic", ["p", "q", "poly"]),
             ("picard_rank", "Picard rank", ["picard_rank", "q", "poly"]),
             ("geometric_picard_rank", "geometric Picard rank", ["geometric_picard_rank", "q", "poly"]),
             ("height", "height", ["height", "q", "poly"]),
             ("angle_rank", "angle rank", ["angle_rank", "q", "poly"]),
             ("k3_count", "K3 points", ["k3_count", "q", "poly"]),
             ("artin_tate_value", "Artin-Tate value", ["artin_tate_value", "q", "poly"]),
             ("geometric_extension_degree", "geometric extension degree", ["geometric_extension_degree", "q", "poly"]),
             ("twist_count", "number of twists", ["twist_count", "q", "poly"])]
    noun = "class"
    plural_noun = "classes"
    jump_example = "2.p.a_a_a_a_a_a_a_a_a_a_a"
    jump_egspan = "e.g. a label, or a polynomial P(T) or L(T) of degree 22"
    jump_knowl = "k3.fq.search_input"
    jump_prompt = "Label or polynomial"
    null_column_explanations = {
        # These columns are null by definition for some classes (rather than not computed):
        # height for supersingular classes, ns_disc_class when the Picard rank is 0,
        # and transcendental_irreducible for supersingular classes
        "height": False,
        "ns_disc_class": False,
        "transcendental_irreducible": False,
    }

    def __init__(self):
        qshort = display_knowl("ag.base_field", "Base field")
        q = TextBox(
            "q",
            label="Cardinality of the %s" % qshort,
            short_label=qshort,
            example="2",
            example_span="2 or 2-5",
        )
        p = TextBox(
            "p",
            label="Characteristic of the %s" % qshort,
            short_label=display_knowl("ag.base_field", "Base char."),
            example="3",
            example_span="3 or 2-5",
        )
        r = TextBox(
            "r",
            label="Degree of the %s" % qshort,
            short_label=display_knowl("ag.base_field", "Base degree"),
            example="1",
            example_span="1 or 1-2",
            advanced=True,
        )
        sign = SelectBox(
            "sign",
            label="Sign",
            knowl="k3.fq.sign",
            options=[("", ""), ("1", "+1"), ("-1", "&minus;1")],
        )
        picard_rank = TextBox(
            "picard_rank",
            label="Picard rank",
            knowl="k3.fq.picard_rank",
            example="2",
            example_span="2 or 1-4",
        )
        geometric_picard_rank = TextBox(
            "geometric_picard_rank",
            label="Geometric Picard rank",
            knowl="k3.fq.geometric_picard_rank",
            short_label="Geom. Picard rank",
            example="4",
            example_span="4 or 2-10",
        )
        height = TextBox(
            "height",
            label="Height",
            knowl="k3.fq.height",
            example="2",
            example_span="2, 1-3 or inf",
        )
        newton = SelectBox(
            "newton",
            label="Newton polygon",
            knowl="k3.fq.newton_polygon",
            options=[("", ""),
                     ("ordinary", "ordinary"),
                     ("supersingular", "supersingular"),
                     ("neither", "neither"),
                     ("not_ordinary", "not ordinary"),
                     ("not_supersingular", "not supersingular")],
        )
        angle_rank = TextBox(
            "angle_rank",
            label="Angle rank",
            knowl="k3.fq.angle_rank",
            example="10",
            example_col=False,
            advanced=True,
        )
        angle_corank = TextBox(
            "angle_corank",
            label="Angle corank",
            knowl="k3.fq.angle_rank",
            example="1",
            example_col=False,
            advanced=True,
        )
        newton_elevation = TextBox(
            "newton_elevation",
            label="Newton elevation",
            knowl="k3.fq.newton_elevation",
            example="1",
            example_col=False,
            advanced=True,
        )
        geometric_extension_degree = TextBox(
            "geometric_extension_degree",
            label="Geometric extension degree",
            knowl="k3.fq.geometric_extension_degree",
            short_label="Geom. ext. degree",
            example="6",
            example_span="6 or 2-12",
            advanced=True,
        )
        initial_coefficients = TextBox(
            "initial_coefficients",
            label="Initial coefficients",
            knowl="k3.fq.initial_coefficients",
            example="[-1, 3]",
        )
        k3_count = TextBox(
            "k3_count",
            label=r"Points on K3 surface",
            knowl="k3.fq.point_counts",
            short_label=r"K3 points",
            example="5",
            example_span="5 or -10-10",
        )
        artin_tate_value = TextBox(
            "artin_tate_value",
            label="Artin&ndash;Tate value",
            knowl="k3.fq.artin_tate",
            example="12",
            example_span="12 or 1-100",
            advanced=True,
        )
        ns_disc_class = TextBox(
            "ns_disc_class",
            label="NS discriminant class",
            knowl="k3.fq.ns_disc_class",
            short_label="NS disc. class",
            example="-3",
            example_span="-3 or 1-5",
            advanced=True,
        )
        ej_condition = YesNoBox(
            "ej_condition",
            label="Artin&ndash;Tate condition",
            knowl="k3.fq.ej_condition",
            short_label="AT condition",
        )
        has_nonnegative_counts = YesNoBox(
            "has_nonnegative_counts",
            label="Nonnegative counts",
            knowl="k3.fq.has_nonnegative_counts",
            advanced=True,
        )
        has_count_growth = YesNoBox(
            "has_count_growth",
            label="Count growth",
            knowl="k3.fq.has_count_growth",
        )
        is_pointless = YesNoBox(
            "is_pointless",
            label="Pointless",
            knowl="k3.fq.pointless",
        )
        is_primitive = YesNoBox(
            "is_primitive",
            label="Primitive",
            knowl="k3.fq.primitive",
        )
        transcendental_irreducible = YesNoBox(
            "transcendental_irreducible",
            label="Irreducible transcendental part",
            knowl="k3.fq.transcendental_part",
            short_label="Irred. trans. part",
            advanced=True,
        )
        has_k3_newton_polygon = YesNoBox(
            "has_k3_newton_polygon",
            label="K3 Newton polygon",
            knowl="k3.fq.newton_polygon",
            advanced=True,
        )
        realizable = {}
        for col, lab, short in [
                ("realizable_k3", "K3 surface", "K3"),
                ("realizable_nck3", "Noncommutative K3", "NC K3"),
                ("realizable_cubic", "Cubic fourfold", "Cubic"),
                ("realizable_nccubic", "Noncommutative cubic", "NC cubic"),
                ("realizable_gm", "Gushel&ndash;Mukai fourfold", "GM"),
                ("realizable_ncgm", "Noncommutative GM", "NC GM"),
                ("realizable_verra", "Verra fourfold", "Verra"),
                ("realizable_ncverra", "Noncommutative Verra", "NC Verra"),
                ("realizable_kummer", "Kummer surface", "Kummer")]:
            realizable[col] = YesNoMaybeBox(
                col,
                label="Contains a " + lab if col == "realizable_k3" else "Realizable: " + lab,
                knowl="k3.fq.realizability",
                short_label=short,
                advanced=(col != "realizable_k3"),
            )
        twist_count = TextBox(
            "twist_count",
            label="Number of twists",
            knowl="k3.fq.twist",
            short_label="# twists",
            example="2",
            example_span="2 or 1-10",
            advanced=True,
        )
        max_twist_degree = TextBox(
            "max_twist_degree",
            label="Max twist degree",
            knowl="k3.fq.twist",
            example="4",
            example_col=False,
            advanced=True,
        )
        geometric_class = TextBox(
            "geometric_class",
            label="Geometric class",
            knowl="k3.fq.twist",
            example="2.p.a_a_a_a_a_a_a_a_a_a_a",
            example_span="a label",
            advanced=True,
        )
        num_lattices = TextBox(
            "num_lattices",
            label="Number of NS lattices",
            knowl="k3.fq.lattices",
            short_label="# lattices",
            example="1",
            example_span="1 or 2-5",
            advanced=True,
        )
        number_field = TextBox(
            "number_field",
            label="Number field",
            knowl="k3.fq.transcendental_number_field",
            example="20.0.123.1",
            example_span="a label",
            advanced=True,
        )
        galois_group = TextBox(
            "galois_group",
            label="Galois group",
            knowl="k3.fq.transcendental_galois_group",
            example="20T1",
            example_span="20T1, or a list of " + display_knowl("nf.galois_group.name", "group names"),
            advanced=True,
        )
        count = CountBox()

        self.refine_array = [
            [q, p, sign, picard_rank, geometric_picard_rank],
            [height, newton, initial_coefficients, k3_count, ej_condition],
            [has_count_growth, is_pointless, is_primitive, realizable["realizable_k3"], has_nonnegative_counts],
            [r, angle_rank, angle_corank, newton_elevation, geometric_extension_degree],
            [artin_tate_value, ns_disc_class, transcendental_irreducible, has_k3_newton_polygon, twist_count],
            [max_twist_degree, geometric_class, num_lattices, number_field, galois_group],
            [realizable["realizable_nck3"], realizable["realizable_cubic"], realizable["realizable_nccubic"], realizable["realizable_gm"], realizable["realizable_ncgm"]],
            [realizable["realizable_verra"], realizable["realizable_ncverra"], realizable["realizable_kummer"]],
        ]
        self.browse_array = [
            [q, sign],
            [p, picard_rank],
            [geometric_picard_rank, height],
            [newton, initial_coefficients],
            [k3_count, ej_condition],
            [has_count_growth, is_pointless],
            [is_primitive, realizable["realizable_k3"]],
            [r, has_nonnegative_counts],
            [angle_rank, angle_corank],
            [newton_elevation, geometric_extension_degree],
            [artin_tate_value, ns_disc_class],
            [transcendental_irreducible, has_k3_newton_polygon],
            [twist_count, max_twist_degree],
            [geometric_class, num_lattices],
            [number_field, galois_group],
            [realizable["realizable_nck3"], realizable["realizable_cubic"]],
            [realizable["realizable_nccubic"], realizable["realizable_gm"]],
            [realizable["realizable_ncgm"], realizable["realizable_verra"]],
            [realizable["realizable_ncverra"], realizable["realizable_kummer"]],
            [count],
        ]

    def search_types(self, info):
        return self._search_again(info, [
            ("List", "List of classes"),
            ("Counts", "Counts table"),
            ("Random", "Random class")])


#########################
#  Search results
#########################

class OptMathCol(MathCol):
    """
    A math column whose value may be null (displayed as blank).
    """
    def display(self, rec):
        val = self.get(rec)
        if val is None or val == "":
            return ""
        return "$%s$" % val


def realizable_col(col, title, default=False):
    return ProcessedCol(col, "k3.fq.realizability", title, realizable_display, default=default, align="center")


k3fq_columns = SearchColumns([
    ProcessedLinkCol("label", "k3.fq.lmfdb_label", "Label", url_for_label, label_wbr),
    MathCol("field", "ag.base_field", "Base field", download_col="q"),
    MathCol("p", "ag.base_field", "Base char.", short_title="base characteristic", default=False),
    MathCol("sign_display", "k3.fq.sign", "Sign", download_col="sign"),
    OptMathCol("picard_rank", "k3.fq.picard_rank", r"$\rho$", short_title="Picard rank"),
    OptMathCol("geometric_picard_rank", "k3.fq.geometric_picard_rank", r"$\bar\rho$", short_title="geometric Picard rank"),
    OptMathCol("height_display", "k3.fq.height", "Height", download_col="height"),
    CheckCol("is_ordinary", "k3.fq.newton_polygon", "Ordinary", default=False),
    CheckCol("is_supersingular", "k3.fq.newton_polygon", "Supersingular", default=False),
    OptMathCol("pretty_slopes", "k3.fq.newton_polygon", "Newton slopes", download_col="slopes", default=False),
    OptMathCol("newton_elevation", "k3.fq.newton_elevation", "Newton elevation", default=False),
    OptMathCol("angle_rank", "k3.fq.angle_rank", "Angle rank"),
    OptMathCol("angle_corank", "k3.fq.angle_rank", "Angle corank", default=False),
    OptMathCol("geometric_extension_degree", "k3.fq.geometric_extension_degree", "Geom. ext. degree", short_title="geometric extension degree", default=False),
    OptMathCol("cyclotomic_display", "k3.fq.cyclotomic_part", "Cyclotomic factors", download_col="cyclotomic_factors", default=False),
    OptMathCol("artin_tate_value", "k3.fq.artin_tate", "$AT_1$", short_title="Artin-Tate value", default=False),
    OptMathCol("ns_disc_class", "k3.fq.ns_disc_class", "NS disc. class", short_title="NS discriminant class", default=False),
    CheckCol("ej_condition", "k3.fq.ej_condition", "AT condition", short_title="Artin-Tate condition", default=False),
    OptMathCol("k3_count", "k3.fq.point_counts", r"$\#X(\mathbb{F}_q)$", short_title="Fq points on K3"),
    OptMathCol("k3_counts", "k3.fq.point_counts", r"$\#X(\mathbb{F}_{q^n})$", short_title="Fq^n points on K3", default=False),
    CheckCol("has_nonnegative_counts", "k3.fq.has_nonnegative_counts", "Nonneg. counts", short_title="nonnegative counts", default=False),
    CheckCol("has_count_growth", "k3.fq.has_count_growth", "Count growth", default=False),
    CheckCol("is_pointless", "k3.fq.pointless", "Pointless", default=False),
    CheckCol("is_primitive", "k3.fq.primitive", "Primitive", default=False),
    OptMathCol("twist_count", "k3.fq.twist", "Num. twists", default=False),
    OptMathCol("max_twist_degree", "k3.fq.twist", "Max. twist degree", default=False),
    realizable_col("realizable_k3", "K3"),
    realizable_col("realizable_nck3", "NC K3"),
    realizable_col("realizable_cubic", "Cubic"),
    realizable_col("realizable_nccubic", "NC cubic"),
    realizable_col("realizable_gm", "GM"),
    realizable_col("realizable_ncgm", "NC GM"),
    realizable_col("realizable_verra", "Verra"),
    realizable_col("realizable_ncverra", "NC Verra"),
    realizable_col("realizable_kummer", "Kummer"),
    OptMathCol("num_lattices", "k3.fq.lattices", "Num. lattices", default=False),
    SearchCol("galois_groups_pretty", "k3.fq.transcendental_galois_group", "Galois groups", download_col="galois_groups"),
    OptMathCol("formatted_polynomial", "k3.fq.k3_polynomial", "$P(T)$", download_col="poly", default=False)],
    db_cols=["label", "q", "p", "r", "sign", "poly", "picard_rank", "geometric_picard_rank", "height",
             "is_ordinary", "is_supersingular", "slopes", "newton_elevation", "angle_rank", "angle_corank",
             "geometric_extension_degree", "cyclotomic_factors", "artin_tate_value", "ns_disc_class",
             "ej_condition", "k3_count", "k3_counts", "has_nonnegative_counts", "has_count_growth",
             "is_pointless", "is_primitive", "twist_count", "max_twist_degree", "galois_groups",
             "num_lattices"] + REALIZABLE_COLUMNS)


def k3fq_postprocess(res, info, query):
    gals = set()
    for rec in res:
        for gal in rec.get("galois_groups") or []:
            if gal:
                gals.add(gal)
    cache = {rec["label"]: rec for rec in db.gps_transitive.search({"label": {"$in": list(gals)}}, ["label", "pretty"])} if gals else {}
    ans = []
    for rec in res:
        cl = WebK3Fq(rec)
        cl.gal_cache = cache
        ans.append(cl)
    return ans


@search_wrap(
    table=isog_table,
    title="Motives of K3 type search results",
    err_title="Motives of K3 type search input error",
    columns=k3fq_columns,
    shortcuts={
        "jump": jump,
        "download": K3Fq_download(),
    },
    postprocess=k3fq_postprocess,
    url_for_label=url_for_label,
    learnmore=learnmore_list,
    bread=lambda: get_bread(("Search results", " ")),
)
def k3fq_search(info, query):
    common_parse(info, query)


@count_wrap(
    template="k3fq-count-results.html",
    table=isog_table,
    groupby=["picard_rank", "q"],
    title="Motives of K3 type count results",
    err_title="Motives of K3 type search input error",
    overall=lambda: K3FqStats()._counts(),
    bread=lambda: get_bread(("Count results", " ")),
)
def k3fq_count(info, query):
    common_parse(info, query)
    urlgen_info = dict(info)
    urlgen_info.pop("hst", None)

    def url_generator(rho, q):
        info_copy = dict(urlgen_info)
        info_copy.pop("search_array", None)
        info_copy.pop("search_type", None)
        info_copy["picard_rank"] = rho
        info_copy["q"] = q
        return url_for("k3fq.index", **info_copy)

    stats = K3FqStats()
    if "picard_rank" in info:
        info["row_heads"] = integer_options(info["picard_rank"], contained_in=stats.picard_ranks)
    else:
        info["row_heads"] = stats.picard_ranks
    if "q" in info:
        info["col_heads"] = integer_options(info["q"], contained_in=stats.qs)
    else:
        info["col_heads"] = stats.qs
    if "p" in query:
        ps = integer_options(info["p"], contained_in=stats.qs)
        info["col_heads"] = [q for q in info["col_heads"] if any(q % p == 0 for p in ps)]
    if not info["col_heads"]:
        raise ValueError("Must include at least one base field")
    info["na_msg"] = '"n/a" means that there are no classes with this Picard rank over this field in the database.'
    info["row_label"] = "Picard rank"
    info["col_label"] = r"Cardinality of base field \(q\)"
    info["url_func"] = url_generator


def k3fq_browse(info):
    info["stats"] = K3FqStats()
    info["picard_ranks"] = list(range(DEGREE + 1))
    info["geometric_picard_ranks"] = list(range(0, DEGREE + 1, 2))
    info["heights"] = list(range(1, 11))
    return render_template(
        "k3fq-index.html",
        title="Motives of K3 type over finite fields",
        info=info,
        bread=get_bread(),
        learnmore=learnmore_list(),
    )


@k3fq_page.route("/stats")
def statistics():
    title = "Motives of K3 type over finite fields: Statistics"
    return render_template(
        "display_stats.html",
        info=K3FqStats(),
        title=title,
        bread=get_bread(("Statistics", " ")),
        learnmore=learnmore_list(),
    )


@k3fq_page.route("/dynamic_stats")
def dynamic_statistics():
    info = to_dict(request.args, search_array=K3FqSearchArray())
    K3FqStats().dynamic_setup(info)
    title = "Motives of K3 type over finite fields: Dynamic statistics"
    return render_template(
        "dynamic_stats.html",
        info=info,
        title=title,
        bread=get_bread(("Dynamic statistics", " ")),
        learnmore=learnmore_list(),
    )


@k3fq_page.route("/random")
@redirect_no_cache
def random_class():
    label = isog_table.random()
    return url_for(".by_label", label=label)


@k3fq_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "k3.fq",
        isog_table,
        url_for_label,
        regex=LABEL_RE,
        title=r"Some interesting motives of K3 type over $\Fq$",
        bread=get_bread(("Interesting", " ")),
        learnmore=learnmore_list()
    )


@k3fq_page.route("/Source")
def how_computed_page():
    t = "Source and acknowledgments for motives of K3 type over finite fields"
    bread = get_bread(("Source", " "))
    return render_template(
        "multi.html",
        kids=["rcs.source.k3.fq",
              "rcs.ack.k3.fq",
              "rcs.cite.k3.fq"],
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Source"),
    )


@k3fq_page.route("/Completeness")
def completeness_page():
    t = "Completeness of the data on motives of K3 type over finite fields"
    bread = get_bread(("Completeness", " "))
    return render_template(
        "single.html",
        kid="rcs.cande.k3.fq",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Completeness"),
    )


@k3fq_page.route("/Reliability")
def reliability_page():
    t = "Reliability of the data on motives of K3 type over finite fields"
    bread = get_bread(("Reliability", " "))
    return render_template(
        "single.html",
        kid="rcs.rigor.k3.fq",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Reliability"),
    )


@k3fq_page.route("/Labels")
def labels_page():
    t = "Labels for motives of K3 type over finite fields"
    bread = get_bread(("Labels", " "))
    return render_template(
        "single.html",
        kid="k3.fq.lmfdb_label",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Labeling"),
    )
