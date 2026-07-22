# -*- coding: utf-8 -*-

from lmfdb.tests import LmfdbTest

class ShimCrvTest(LmfdbTest):
    def test_home(self):
        L = self.tc.get('/ShimuraCurve/Q/')
        assert 'Shimura curves' in L.get_data(as_text=True)
        assert 'Browse' in L.get_data(as_text=True)
        assert 'Search' in L.get_data(as_text=True)
        assert 'Find' in L.get_data(as_text=True)
        assert 'X_0(N)' in L.get_data(as_text=True)

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
