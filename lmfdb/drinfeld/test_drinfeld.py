import pytest

from lmfdb.tests import LmfdbTest
from lmfdb.drinfeld.main import char_poly_coefficients
from lmfdb.utils.search_parsing import SearchParsingError


class DrinfeldTest(LmfdbTest):
    def test_index(self):
        page = self.tc.get("/DrinfeldModule/Fq/").get_data(as_text=True)
        assert "isogeny classes" in page
        assert "Browse" in page

    def test_isogeny_class(self):
        page = self.tc.get("/DrinfeldModule/Fq/2.2.2.2_7").get_data(as_text=True)
        assert "X^{2} + T X + T^{2} + T + 1" in page
        assert "2.2.2.2_7.1" in page and "2.2.2.2_7.2" in page

    def test_module(self):
        page = self.tc.get("/DrinfeldModule/Fq/2.2.2.2_7.1").get_data(as_text=True)
        assert r"a \tau^{2} + a" in page
        assert r"\F_{4}^\times" in page  # automorphism group
        assert r"\F_q[T]/(T) \oplus \F_q[T]/(T)" in page  # rational points

    def test_isogeny_search(self):
        page = self.tc.get("/DrinfeldModule/Fq/?q=2&n=2&rank=2").get_data(as_text=True)
        assert "12 matches" in page
        page = self.tc.get("/DrinfeldModule/Fq/?q=2&n=2&rank=2&char_poly=T^2%2BT%2B1").get_data(as_text=True)
        assert "4 matches" in page

    def test_module_search(self):
        page = self.tc.get("/DrinfeldModule/Fq/?search_type=Modules&q=2&n=2&rank=2").get_data(as_text=True)
        assert "18 matches" in page

    def test_char_poly_parser(self):
        assert char_poly_coefficients("T^2 + T + 2", 3) == [2, 1, 1]
        assert char_poly_coefficients("T**2 - 1", 3) == [2, 0, 1]
        assert char_poly_coefficients("T + b", 4) == [2, 1]
        assert char_poly_coefficients("(T + b + 1)(T + b)", 4) == [1, 1, 1]
        assert char_poly_coefficients("T^100", 2)[-1] == 1
        # Degree is bounded before any power or product is formed
        for inp in ["T^101", "T**1000", "T**100000000000", "T^999^999", "T**2**3",
                    "(T^999)^999", "(T^50)(T^51)", "((T^10)^10)^10", "T^(9^9)"]:
            with pytest.raises(SearchParsingError):
                char_poly_coefficients(inp, 2)
        for inp, q in [("2*T + 1", 3), ("T + b", 3), ("__import__('os')", 2), ("T + 1", 6), ("T + 1", 2**20)]:
            with pytest.raises(SearchParsingError):
                char_poly_coefficients(inp, q)

    def test_char_poly_search_bounded(self):
        page = self.tc.get("/DrinfeldModule/Fq/?q=2&char_poly=(T^999)^999").get_data(as_text=True)
        assert "degree must be at most" in page

    def test_filters_across_search_types(self):
        # isogeny invariants restrict module searches, and vice versa
        page = self.tc.get("/DrinfeldModule/Fq/?search_type=Modules&q=2&n=2&rank=2&height=2").get_data(as_text=True)
        assert "7 matches" in page
        page = self.tc.get("/DrinfeldModule/Fq/?q=2&n=2&rank=2&automorphisms=3").get_data(as_text=True)
        assert "7 matches" in page

    def test_char_poly_needs_q(self):
        page = self.tc.get("/DrinfeldModule/Fq/?char_poly=T%2B1").get_data(as_text=True)
        assert "single prime power q" in page

    def test_bad_label(self):
        page = self.tc.get("/DrinfeldModule/Fq/not_a_label", follow_redirects=True).get_data(as_text=True)
        assert "not a valid label" in page

    def test_stats(self):
        page = self.tc.get("/DrinfeldModule/Fq/stats").get_data(as_text=True)
        assert "height" in page

    def test_data(self):
        page = self.tc.get("/DrinfeldModule/Fq/data/2.2.2.2_7").get_data(as_text=True)
        assert "frob_poly" in page
