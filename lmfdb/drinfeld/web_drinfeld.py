import re

from flask import url_for
from sage.all import ZZ, QQ, conway_polynomial, lazy_attribute

from lmfdb import db
from lmfdb.utils import WebObj, display_knowl

ISOG_LABEL_RE = re.compile(r"[1-9]\d*\.[1-9]\d*\.[1-9]\d*\.\d+(_\d+)*")
MODULE_LABEL_RE = re.compile(r"[1-9]\d*\.[1-9]\d*\.[1-9]\d*\.\d+(_\d+)*\.[1-9]\d*")


def get_bread(tail=[]):
    base = [("Drinfeld modules", url_for(".index")), (r"$\F_q$", url_for(".index_Fq"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail


def url_for_label(label):
    return url_for("drinfeld.by_label", label=label)


def sage_tex(s):
    """
    TeX for a polynomial as Sage prints it, in T, X, tau and the generators a, b.
    """
    s = s.replace("*", " ").replace("τ", r"\tau ")
    return re.sub(r"\^(\d+)", r"^{\1}", s).replace(" ^", "^")


def split_sage_list(s):
    """
    The entries of a list printed by Sage, such as ``[1, (a + 1)*τ^2 + τ]``.
    """
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    entries, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            entries.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        entries.append(cur.strip())
    return entries


def field_tex(q):
    return r"\F_{%s}" % q


def module_points_tex(module_points_str):
    parts = [r"\F_q[T]/(%s)" % sage_tex(g) for g in split_sage_list(module_points_str)]
    return r" \oplus ".join(parts) if parts else "0"


def height_tex(height, rank):
    s = "$%s$" % height
    if height == 1 and rank > 1:
        s += " (%s)" % display_knowl("drinfeld.ordinary", "ordinary")
    elif height == rank:
        s += " (%s)" % display_knowl("drinfeld.supersingular", "supersingular")
    return s


class DrinfeldBase(WebObj):
    """
    Data shared by isogeny classes and isomorphism classes: the fields and the A-characteristic.
    """
    @lazy_attribute
    def k(self):
        # q = p^k
        return ZZ(self.q).exact_log(self.p)

    @lazy_attribute
    def L_tex(self):
        return field_tex(self.q ** self.n)

    @lazy_attribute
    def Fq_tex(self):
        return field_tex(self.q)

    @lazy_attribute
    def generators(self):
        """
        Sentences explaining the names a and b used in the stored strings.
        """
        p, k, n = self.p, self.k, self.n
        out = []
        if n > 1:
            out.append(r"$a$ is a root of the %s $%s$, so $%s = \F_{%s}(a)$" % (
                display_knowl("field.finite.conway_polynomial", "Conway polynomial"),
                sage_tex(str(conway_polynomial(p, n * k).change_ring(ZZ))),
                self.L_tex, p))
        if k > 1:
            s = r"$b$ is a root of the %s $%s$" % (
                display_knowl("field.finite.conway_polynomial", "Conway polynomial"),
                sage_tex(str(conway_polynomial(p, k).change_ring(ZZ))))
            if n > 1:
                s += r", and $b = a^{%s}$" % ((self.q ** n - 1) // (self.q - 1))
            out.append(s)
        return out

    @lazy_attribute
    def char_poly_tex(self):
        return sage_tex(self.char_poly_str)

    @lazy_attribute
    def char_degree(self):
        return len(self.char_poly) - 1


class WebDrinfeldIsogenyClass(DrinfeldBase):
    table = db.drinfeld_isog

    @lazy_attribute
    def modules(self):
        return list(db.drinfeld_modules.search(
            {"isogeny_label": self.label},
            ["label", "ore_poly", "ore_poly_str", "automorphisms", "module_points_str"],
            sort=["ore_poly"]))

    @lazy_attribute
    def modules_sorted(self):
        rows = sorted(self.modules, key=lambda m: int(m["label"].split(".")[-1]))
        for m in rows:
            m["ore_tex"] = sage_tex(m["ore_poly_str"])
            m["points_tex"] = module_points_tex(m["module_points_str"])
        return rows

    @lazy_attribute
    def gamma_names(self):
        return dict(zip(self.possible_gamma, split_sage_list(self.possible_gamma_str)))

    @lazy_attribute
    def gamma_used(self):
        """
        TeX for the value of gamma(T) shared by the representatives below, if they share one.
        """
        gammas = {m["ore_poly"][0] for m in self.modules}
        if len(gammas) == 1:
            g = gammas.pop()
            return sage_tex(self.gamma_names.get(g, str(g)))

    @lazy_attribute
    def possible_gamma_tex(self):
        return ", ".join(sage_tex(g) for g in split_sage_list(self.possible_gamma_str))

    @lazy_attribute
    def frob_poly_tex(self):
        return sage_tex(self.frob_poly_str)

    @lazy_attribute
    def weighted_size_tex(self):
        q = QQ(self.weighted_size_Q)
        if q.denominator() == 1:
            return str(q)
        return r"\frac{%s}{%s}" % (q.numerator(), q.denominator())

    @lazy_attribute
    def height_tex(self):
        return height_tex(self.height, self.rank)

    @lazy_attribute
    def title(self):
        return "Drinfeld module isogeny class %s" % self.label

    @lazy_attribute
    def properties(self):
        return [
            ("Label", self.label),
            ("Base field", "$%s$" % self.L_tex),
            ("Rank", "$%s$" % self.rank),
            ("Characteristic", "$%s$" % self.char_poly_tex),
            ("Height", "$%s$" % self.height),
            ("Isomorphism classes", "$%s$" % self.size),
        ]

    @lazy_attribute
    def bread(self):
        return get_bread([(self.label, " ")])

    @lazy_attribute
    def friends(self):
        return []

    @lazy_attribute
    def downloads(self):
        return [("Underlying data", url_for(".drinfeld_data", label=self.label))]


class WebDrinfeldModule(DrinfeldBase):
    table = db.drinfeld_modules

    @lazy_attribute
    def isogeny_class(self):
        return db.drinfeld_isog.lookup(self.isogeny_label)

    @lazy_attribute
    def ore_poly_tex(self):
        return sage_tex(self.ore_poly_str)

    @lazy_attribute
    def gamma_tex(self):
        names = dict(zip(self.isogeny_class["possible_gamma"],
                         split_sage_list(self.isogeny_class["possible_gamma_str"])))
        g = self.ore_poly[0]
        return sage_tex(names.get(g, str(g)))

    @lazy_attribute
    def frob_poly_tex(self):
        return sage_tex(self.isogeny_class["frob_poly_str"])

    @lazy_attribute
    def height(self):
        return self.isogeny_class["height"]

    @lazy_attribute
    def height_tex(self):
        return height_tex(self.height, self.rank)

    @lazy_attribute
    def aut_degree(self):
        # #Aut = q^d - 1, and Aut is the multiplicative group of F_{q^d}
        return ZZ(self.automorphisms + 1).exact_log(self.q)

    @lazy_attribute
    def aut_tex(self):
        return r"\F_{%s}^\times" % (self.q ** self.aut_degree)

    @lazy_attribute
    def endomorphisms_tex(self):
        return [sage_tex(u) for u in split_sage_list(self.endomorphisms_str)]

    @lazy_attribute
    def module_points_tex(self):
        return module_points_tex(self.module_points_str)

    @lazy_attribute
    def title(self):
        return "Drinfeld module %s" % self.label

    @lazy_attribute
    def properties(self):
        return [
            ("Label", self.label),
            ("Base field", "$%s$" % self.L_tex),
            ("Rank", "$%s$" % self.rank),
            ("Characteristic", "$%s$" % self.char_poly_tex),
            ("Height", "$%s$" % self.height),
            ("Automorphisms", "$%s$" % self.automorphisms),
        ]

    @lazy_attribute
    def bread(self):
        return get_bread([(self.isogeny_label, url_for_label(self.isogeny_label)),
                          (self.label.split(".")[-1], " ")])

    @lazy_attribute
    def friends(self):
        return [("Isogeny class " + self.isogeny_label, url_for_label(self.isogeny_label))]

    @lazy_attribute
    def downloads(self):
        return [("Underlying data", url_for(".drinfeld_data", label=self.label))]
