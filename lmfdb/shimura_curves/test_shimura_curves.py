# -*- coding: utf-8 -*-

from lmfdb.tests import LmfdbTest

class ShimCrvTest(LmfdbTest):
    def test_home(self):
        L = self.tc.get('/ShimuraCurve/Q/')
        page = L.get_data(as_text=True)
        assert 'Shimura curves' in page
        assert 'Browse' in page
        assert 'Search' in page
        assert 'Find' in page
        # Assert real Shimura-curve content: this database parametrizes abelian
        # surfaces with PQM and browses by families X(D;1), X(D;N), ... .  The
        # copied-over test asserted the modular-curve string 'X_0(N)', which does
        # not appear on this page.
        assert 'abelian surfaces' in page
        assert 'X(D;1)' in page

    def test_curve_page(self):
        # A known Shimura curve page should load, show its label, and identify
        # itself as a Shimura curve.
        label = '10.1.1.4.0.a.1'
        L = self.tc.get('/ShimuraCurve/Q/%s/' % label)
        assert L.status_code == 200
        page = L.get_data(as_text=True)
        assert label in page
        assert 'Shimura curve' in page

    def test_download(self):
        # All three download routes must return 200 with the label in the payload.
        # Regression test for the download_to_sage typo (T24 item 1): that route
        # called a nonexistent method and 500'd.
        label = '10.1.1.4.0.a.1'
        for route in ['download_to_magma', 'download_to_sage', 'download_to_text']:
            L = self.tc.get('/ShimuraCurve/%s/%s' % (route, label))
            assert L.status_code == 200, "%s returned %s" % (route, L.status_code)
            data = L.get_data(as_text=True)
            assert label in data, "%s payload missing label %s" % (route, label)
        # Magma and Sage payloads are derived from the same Magma source string.
        magma = self.tc.get('/ShimuraCurve/download_to_magma/%s' % label).get_data(as_text=True)
        assert 'Magma code for Shimura curve' in magma
