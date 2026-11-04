import unittest

from lmfdb import db
from lmfdb.tests import LmfdbTest

# The table is not yet available in every copy of the database (e.g. devmirror)
HAS_TABLE = "k3_fq_isog" in db.tablenames

# P(T) = 2(1-T)^22, supersingular over F_2
SS_LABEL = "2.p.abs_ru_aeom_vqs_aczxs_imtm_atkou_bkkbs_aceprc_cvpea_adchca"
# P(T) = 2(1-T)^21(1+T), supersingular with sign -1
SS_MINUS_LABEL = "2.m.abo_oo_adie_nuc_abqmy_dwiw_ahbmm_jyam_akhoy_grya_a"


class K3FqLabelTest(unittest.TestCase):
    # These do not need the database
    def test_labels(self):
        from lmfdb.k3fq.web_k3fq import poly_to_label, label_to_poly, validate_label, lpoly_to_poly
        poly = [2, -44, 462, -3080, 14630, -52668, 149226, -341088, 639540, -994840, 1293292, -1410864,
                1293292, -994840, 639540, -341088, 149226, -52668, 14630, -3080, 462, -44, 2]
        assert poly_to_label(poly) == SS_LABEL
        assert label_to_poly(SS_LABEL) == poly
        lpoly = [1] + [2**(i - 1) * a for i, a in enumerate(poly) if i > 0]
        assert lpoly_to_poly(lpoly) == poly
        validate_label(SS_MINUS_LABEL)
        assert label_to_poly(SS_MINUS_LABEL)[-1] == -2
        for bad in ["2.p.a_a", "6.p.a_a_a_a_a_a_a_a_a_a_a", "2.m.a_a_a_a_a_a_a_a_a_a_b",
                    "2.x.a_a_a_a_a_a_a_a_a_a_a", "2.p.aa_a_a_a_a_a_a_a_a_a_a", "02.p.a_a_a_a_a_a_a_a_a_a_a"]:
            self.assertRaises(ValueError, validate_label, bad)


@unittest.skipUnless(HAS_TABLE, "k3_fq_isog is not in this database")
class K3FqTest(LmfdbTest):
    def test_index(self):
        self.check_args("/Motive/K3/Fq/", ["Motives of K3 type over finite fields", "Browse", "Find"])

    def test_static_pages(self):
        for page in ["Source", "Completeness", "Reliability", "Labels"]:
            self.assertEqual(self.tc.get("/Motive/K3/Fq/" + page).status_code, 200)

    def test_supersingular(self):
        self.check_args("/Motive/K3/Fq/" + SS_LABEL, ["supersingular", r"\infty", r"( 1 - T )^{22}", "Transcendental part"])

    def test_sign_minus(self):
        self.check_args("/Motive/K3/Fq/" + SS_MINUS_LABEL, ["$-1$", r"\rho = 21"])

    def test_bad_label(self):
        self.check_args("/Motive/K3/Fq/2.p.a_a_a", "not a valid label")
        self.check_args("/Motive/K3/Fq/2.p.b_a_a_a_a_a_a_a_a_a_a", "not in the database")

    def test_jump(self):
        self.check_args("/Motive/K3/Fq/?jump=2*(1-T)^22", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?jump=" + SS_LABEL, SS_LABEL)
        self.check_args("/Motive/K3/Fq/?jump=garbage", "is not valid input")

    def test_search(self):
        self.check_args("/Motive/K3/Fq/?q=2", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&height=inf&sign=-1", SS_MINUS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&initial_coefficients=[-44,462]", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&picard_rank=22&newton=supersingular", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?height=foo", "is not a valid input")

    def test_random(self):
        self.check_args("/Motive/K3/Fq/random", "Motive of K3 type")

    def test_stats(self):
        self.check_args("/Motive/K3/Fq/stats", "Distribution of")

    def test_downloads(self):
        self.check_args("/Motive/K3/Fq/download_all/" + SS_LABEL, '"label": "%s"' % SS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&height=inf&Submit=sage&download=1&query=%7B%27q%27%3A+2%2C+%27height%27%3A+None%7D", SS_LABEL)
