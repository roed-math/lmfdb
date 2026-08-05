import os
import re

from lmfdb.tests import LmfdbTest


def szpiro_generator():
    """The scripts/ecnf/generate_szpiro_ratio.py module, loaded by path.

    ``scripts`` is not part of the lmfdb package, so it cannot simply be
    imported; ``None`` is returned when it is absent (e.g. when only the
    package has been installed).
    """
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir,
                        "scripts", "ecnf", "generate_szpiro_ratio.py")
    if not os.path.exists(path):
        return None
    spec = importlib.util.spec_from_file_location("generate_szpiro_ratio", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EllCurveTest(LmfdbTest):

    # All tests should pass
    #
    def test_minimal_eqn(self):
        r"""
        Check that the elliptic curve/#field tells about (non)existence of a global minimal model
        """
        L = self.tc.get('/EllipticCurve/2.2.89.1/81.1/a/1')
        assert 'This is a <a title="Global minimal model' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/2.2.229.1/9.3/a/2')
        assert 'This is not a <a title="Global minimal model' in L.get_data(as_text=True)
        assert 'at all primes except' in L.get_data(as_text=True)

    def test_base_field(self):
        r"""
        Check that the elliptic curve/#field tells about its base field
        """
        L = self.tc.get('/EllipticCurve/3.1.23.1/89.1/A/1')
        assert '3.1.23.1' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/2.2.5.1/49.1/a/2')
        assert r'\phi' in L.get_data(as_text=True)

    def test_bad_red(self):
        r"""
        Check that the elliptic curve/#field tells about its bad reduction primes
        """
        L = self.tc.get('/EllipticCurve/2.2.5.1/31.2/a/3')
        assert 'Non-split multiplicative' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/2.2.5.1/64.1/a/1')
        assert 'Additive' in L.get_data(as_text=True)

    def test_weierstrass(self):
        r"""
        Check that the elliptic curve/#field tells about its Weirstrass eqn
        """
        L = self.tc.get('/EllipticCurve/2.0.4.1/225.2/a/2')
        assert '396' in L.get_data(as_text=True)
        assert '2982' in L.get_data(as_text=True)

    def test_conductor(self):
        r"""
        Check that the elliptic curve/#field tells about its conductor
        and discriminant
        """
        L = self.tc.get('/EllipticCurve/2.0.7.1/10000.5/a/1')
        assert '10000' in L.get_data(as_text=True)
        assert '15625000000000000' in L.get_data(as_text=True)
        assert '87890625' in L.get_data(as_text=True)
        assert '25^{9}' in L.get_data(as_text=True)
        assert '12' in L.get_data(as_text=True)

    def test_j(self):
        r"""
        Check that the elliptic curve/#field tells about its j invariant
        """
        L = self.tc.get('/EllipticCurve/2.0.4.1/5525.5/b/9')
        assert '226834389543384' in L.get_data(as_text=True)
        assert '1490902050625' in L.get_data(as_text=True)
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1') # Test factorisation
        assert '8798344145175011328000' in L.get_data(as_text=True)

    def test_download(self):
        r"""
        Check that the code download links work
        """
        L = self.tc.get('/EllipticCurve/2.0.4.1/5525.5/b/9')
        assert 'Magma commands' in L.get_data(as_text=True)
        assert 'SageMath commands' in L.get_data(as_text=True)
        assert 'PariGP commands' in L.get_data(as_text=True)
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1/download/magma')
        assert 'Magma code for working with elliptic curve 2.2.89.1-81.1-a1' in L.get_data(as_text=True)
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1/download/sage')
        assert 'SageMath code for working with elliptic curve 2.2.89.1-81.1-a1' in L.get_data(as_text=True)
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1/download/gp')
        assert 'Pari/GP code for working with elliptic curve 2.2.89.1-81.1-a1' in L.get_data(as_text=True)

    def test_search(self):
        r"""
        Check ecnf search results
        """
        # Conductor 1
        L = self.tc.get('/EllipticCurve/?start=0&count=50&conductor_norm=1&include_isogenous=on&include_base_change=on')
        assert '2115 a - 13286543' in L.get_data(as_text=True)
        # 4*4 torsion
        L = self.tc.get('/EllipticCurve/?start=0&count=50&include_isogenous=on&include_base_change=on&torsion=&torsion_structure=[4%2C4]')
        assert '/EllipticCurve/2.0.4.1/5525.5/b/9' in L.get_data(as_text=True)
        # 13 torsion
        L = self.tc.get('/EllipticCurve/?torsion=13')
        assert '2745' in L.get_data(as_text=True)
        assert '3.3.49.1' in L.get_data(as_text=True)
        #field (see what I did here?)
        L = self.tc.get('/EllipticCurve/?field=Qsqrt-11&include_base_change=on&conductor_norm=&include_isogenous=on&torsion=&torsion_structure=&count=')
        assert '2.0.11.1' in L.get_data(as_text=True)
        assert '1681' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/?jinv=0,1728')
        t = L.get_data(as_text=True)
        assert '729.1-CMb1' in t and '1024.1-a1' in t and '73.1-a1' not in t
        L = self.tc.get('/EllipticCurve/?field=2.0.11.1&jinv=~-52893159101157376/11')
        assert '11.1-a1' not in L.get_data(as_text=True)
        # Test regulator search
        L = self.tc.get('/EllipticCurve/?regulator=8.4-9.1')
        t = L.get_data(as_text=True)
        assert '14763.2-b4' in t and '73.1-a1' not in t

    def test_browse(self):
        r"""
        Check that degree browse pages display correctly
        """
        for n, cnt in [(2, 77095), (3, 4416), (4, 4064), (5, 792), (6, 537)]:
            self.check_args(f"/EllipticCurve/browse/{n}", str(cnt))

    def test_isodeg(self):
        r"""
        Test that searching for isogeny degree works
        """
        L = self.tc.get('/EllipticCurve/?start=0&isodeg=2')
        assert '73.1-a1' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/?start=0&torsion=1&isodeg=2')
        assert 'No matches' in L.get_data(as_text=True)

    def test_szpiro_ratio(self):
        r"""
        Test that the Szpiro ratio is displayed, searchable and sortable
        once ec_nfcurves has the szpiro_ratio column, and that the pages
        still work (without offering it) while the column is missing
        """
        from lmfdb.ecnf.main import HAVE_SZPIRO_RATIO
        # 2.2.5.1-31.1-a1 has Szpiro ratio exactly 1 (Norm(D_min) = Norm(N) = 31);
        # 3.3.1369.1-1.1-a1 has everywhere good reduction, so no ratio at all.
        curve_url = '/EllipticCurve/2.2.5.1/31.1/a/1'
        egr_url = '/EllipticCurve/3.3.1369.1/1.1/a/1'
        t = self.tc.get(curve_url).get_data(as_text=True)
        assert 'Conductor norm' in t

        if not HAVE_SZPIRO_RATIO:
            # Compatibility branch: the pages load and offer no ratio anywhere.
            # A szpiro_ratio constraint is deliberately ignored rather than
            # raising, so the search below only shows that the page still works;
            # it says nothing about filtering, which needs the column.
            assert 'Szpiro ratio' not in t
            assert 'Szpiro ratio' not in self.tc.get('/EllipticCurve/').get_data(as_text=True)
            assert self.tc.get('/EllipticCurve/?field=2.2.5.1&szpiro_ratio=0.5-1.5').status_code == 200
            return

        # Displayed on the curve page, with the right value.  Match the label
        # text rather than the knowl markup around it: KNOWL() renders a plain
        # label until ec.szpiro_ratio has been created, and an anchor after.
        row = re.search(r'Szpiro ratio.*?</tr>', t, re.DOTALL)
        assert row is not None, 'no Szpiro ratio row on %s' % curve_url
        assert re.search(r'\$\s*1\.0\s*\$', row.group(0)), row.group(0)
        # Omitted for a curve with everywhere good reduction, where it is undefined.
        assert 'Szpiro ratio' not in self.tc.get(egr_url).get_data(as_text=True)

        # A range containing 1.0 finds the curve and a disjoint range does not:
        # the pair is what shows that the constraint reaches the query at all.
        t = self.tc.get('/EllipticCurve/?field=2.2.5.1&szpiro_ratio=0.5-1.5').get_data(as_text=True)
        assert curve_url in t
        t = self.tc.get('/EllipticCurve/?field=2.2.5.1&szpiro_ratio=1.1-1.5').get_data(as_text=True)
        assert curve_url not in t

        # Sorting by the ratio works, and shows the column even though it is
        # off by default: without the sort its results-table header carries
        # display:none (it is always in the html, for the column selector).
        L = self.tc.get('/EllipticCurve/?field=2.2.5.1&sort_order=szpiro_ratio')
        assert L.status_code == 200
        th = re.search(r'<th class="col-szpiro_ratio" style="([^"]*)"', L.get_data(as_text=True))
        assert th is not None, 'no Szpiro ratio column in the results table'
        assert 'display:none' not in th.group(1), th.group(0)

    def test_szpiro_ratio_generator(self):
        r"""
        Test the helpers of scripts/ecnf/generate_szpiro_ratio.py, which
        do not depend on ec_nfcurves having the szpiro_ratio column
        """
        gen = szpiro_generator()
        if gen is None:
            self.skipTest("scripts/ecnf/generate_szpiro_ratio.py is not in this checkout")
        # 2.2.5.1-31.1-a1: Norm(D_min) = Norm(N) = 31, so sigma = 1 exactly.
        assert gen.szpiro_ratio(31, 31) == 1.0
        # Everywhere good reduction: both norms are 1 and sigma is undefined.
        assert gen.szpiro_ratio(1, 1) is None
        # Trivial conductor with nontrivial minimal discriminant is impossible.
        with self.assertRaises(ValueError):
            gen.szpiro_ratio(2, 1)
        with self.assertRaises(ValueError):
            gen.szpiro_ratio(0, 31)

        # A synthetic non-minimal row, modelled on 2.0.31.1-256.7-a1: the
        # stored model is non-minimal at (2,w), so its discriminant norm is
        # normp^12 = 2^12 times the norm of the minimal discriminant, and both
        # formulas must give Norm(D_min) = 2^4 * 2^10.
        rec = {'label': 'test.curve',
               'non_min_p': ['(2,w)'],
               'local_data': [{'p': '(2,w)', 'normp': 2, 'ord_disc': 4},
                              {'p': '(2,w+1)', 'normp': 2, 'ord_disc': 10}],
               'normdisc': -2**26}
        assert gen.min_disc_norm(rec) == 2**14
        assert gen.min_disc_norm_from_normdisc(rec) == 2**14

        # Local data missing for a prime listed in non_min_p: say which curve
        # and which prime rather than failing on a StopIteration.
        broken = dict(rec, local_data=rec['local_data'][1:])
        with self.assertRaises(ValueError) as cm:
            gen.min_disc_norm_from_normdisc(broken)
        assert 'test.curve' in str(cm.exception) and '(2,w)' in str(cm.exception)

        # normdisc not divisible by normp^12 at a non-minimal prime.
        broken = dict(rec, normdisc=-(2**26 + 1))
        with self.assertRaises(ValueError) as cm:
            gen.min_disc_norm_from_normdisc(broken)
        assert 'test.curve' in str(cm.exception)

    def test_cm_disc_search(self):
        r"""
        Test that searching for CM field discriminant works
        """
        self.check_args('/EllipticCurve/?cm_disc=-4','1024.1-a1')
        self.not_check_args('/EllipticCurve/?cm_disc=-4','1.0.1-a1')

        # make sure it works with 4-way PCM, CM, PCMnoCM, noCM switch
        self.check_args('/EllipticCurve/?cm_disc=-11&include_cm=PCMnoCM','14641.1-a1')
        self.not_check_args('/EllipticCurve/?cm_disc=-11&include_cm=PCMnoCM','9.1-CMa1')

    def test_related_objects(self):
        for url, text in [('/EllipticCurve/2.0.8.1/324.3/a/1',
                ['Isogeny class 324.3-a',
                 'Twists',
                 'Base change of 36.a4',
                 'Base change of 576.f3',
                 'Bianchi modular form 2.0.8.1-324.3-a',
                 'Hilbert modular form 2.2.24.1-36.1-a',
                 'Elliptic curve 2.2.24.1-36.1-a',
                 'Genus 2 curve 20736.i',
                 'L-function']),
                ('/EllipticCurve/2.0.11.1/256.1/b/1',
                    ['Isogeny class 256.1-b',
                     'Twists',
                     'Bianchi modular form 2.0.11.1-256.1-a',
                     'Bianchi modular form 2.0.11.1-256.1-b',
                     'Hilbert modular form 2.2.44.1-16.1-a',
                     'Hilbert modular form 2.2.44.1-16.1-c',
                     'Elliptic curve 2.0.11.1-256.1-a',
                     'Elliptic curve 2.2.44.1-16.1-a',
                     'Elliptic curve 2.2.44.1-16.1-c',
                     'L-function'])]:
            L = self.tc.get(url).get_data(as_text=True)
            for t in text:
                assert t in L
