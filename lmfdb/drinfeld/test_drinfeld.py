from lmfdb.tests import LmfdbTest


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
