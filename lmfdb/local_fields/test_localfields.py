from lmfdb.tests import LmfdbTest


class LocalFieldTest(LmfdbTest):

    # All tests should pass
    #
    def test_search_ramif_cl_deg(self):
        L = self.tc.get('/padicField/?n=8&c=24&gal=8T5&p=2&e=8&count=20')
        assert '4 matches' in L.get_data(as_text=True)

    def test_search_f(self):
        L = self.tc.get('/padicField/?n=6&p=2&f=3')
        dat = L.get_data(as_text=True)
        assert '2.2.3.4a1.1' not in dat
        assert '2.3.2.6a1.2' in dat

    def test_search_top_slope(self):
        L = self.tc.get('/padicField/?p=2&topslope=3.5')
        assert '2.1.4.9a1.1' in L.get_data(as_text=True) # number of matches
        L = self.tc.get('/padicField/?p=2&topslope=3.4..3.55')
        assert '2.1.4.9a1.1' in L.get_data(as_text=True) # number of matches
        L = self.tc.get('/padicField/?p=2&topslope=7/2')
        assert '2.1.4.9a1.1' in L.get_data(as_text=True) # number of matches

    def test_stats_pages(self):
        # The browse page and statistics page link to dynamic statistics
        L = self.tc.get('/padicField/')
        assert 'dynamic_stats' in L.get_data(as_text=True)
        L = self.tc.get('/padicField/stats')
        dat = L.get_data(as_text=True)
        assert 'create your own' in dat and 'dynamic_stats' in dat

    def test_dynamic_stats(self):
        # A combination whose statistics are precomputed: degree x ramification index for p=2
        # (there are 6 totally ramified quadratic extensions of Q_2)
        L = self.tc.get('/padicField/dynamic_stats?p=2&col1=n&totals1=yes&col2=e&proportions=rows&search_type=DynStats')
        dat = L.get_data(as_text=True)
        assert 'n=2&amp;e=2' in dat and '>6<' in dat
        # Galois groups for p=2, n=4 (also precomputed); 12 of the 59 quartic
        # 2-adic fields are cyclic
        L = self.tc.get('/padicField/dynamic_stats?p=2&n=4&col1=galois_label&proportions=none&search_type=DynStats')
        dat = L.get_data(as_text=True)
        assert 'C_4' in dat and '>12<' in dat
        # All column options render (values for most combinations are computed and
        # cached on demand, so against a read-only database the tables may be empty,
        # but the pages should not error)
        for col in ['p', 'n', 'e', 'f', 'c', 'galois_label', 'aut', 'u', 't', 'top_slope',
                    'slopes', 'visible', 'hidden', 'ind_of_insep', 'associated_inertia', 'jump_set']:
            L = self.tc.get('/padicField/dynamic_stats?col1=%s&proportions=recurse&search_type=DynStats' % col)
            assert L.status_code == 200
            other = 'p' if col == 'n' else 'n'
            L = self.tc.get('/padicField/dynamic_stats?col1=%s&col2=%s&totals1=yes&totals2=yes&proportions=rows&search_type=DynStats' % (col, other))
            assert L.status_code == 200

    def test_dynamic_stats_null_query_formatters(self):
        # Not-computed / empty values have no search representation, so their
        # query_formatters return the NO_SEARCH_QUERY sentinel and the drill-down link
        # is suppressed rather than pointing at an unfiltered search (LMFDB#6542).
        from lmfdb.local_fields.main import (
            LFStats, NO_SEARCH_QUERY, galquery, bracket_query, content_query,
            nullable_int_query, formatbracketcol)
        # Null / empty -> sentinel; genuine values -> a real search fragment
        assert galquery(None) == NO_SEARCH_QUERY
        assert galquery('1T1') == 'gal=1T1'
        assert nullable_int_query('u')(None) == NO_SEARCH_QUERY
        assert nullable_int_query('u')(2) == 'u=2'
        assert bracket_query('associated_inertia')(None) == NO_SEARCH_QUERY
        assert bracket_query('associated_inertia')([1, 2]) == 'associated_inertia=[1, 2]'
        cq = content_query('slopes', 'slopes_quantifier')
        assert cq(None) == NO_SEARCH_QUERY and cq([]) == NO_SEARCH_QUERY and cq('[]') == NO_SEARCH_QUERY
        assert cq('[2, 2]') == 'slopes=[2, 2]&slopes_quantifier=exactly'
        assert LFStats.query_formatters['hidden'](None) == NO_SEARCH_QUERY
        assert LFStats.query_formatters['hidden']('') == NO_SEARCH_QUERY
        # None array columns render as "not computed", never a literal $None$ (P3)
        assert formatbracketcol(None) == 'not computed'
        assert formatbracketcol('') == 'not computed'
        assert formatbracketcol([]) == r'$[\ ]$'
        assert formatbracketcol([1, 2]) == '$[1, 2]$'
        # display_data blanks a sentinel-bearing drill-down while keeping real ones
        base = '/padicField/?'
        data = {'counts': [
            {'value': 'not computed', 'count': 5, 'query': base + NO_SEARCH_QUERY},
            {'value': 'C_4', 'count': 7, 'query': base + 'gal=4T1'}]}
        LFStats._suppress_null_links(data)
        assert data['counts'][0]['query'] == ''
        assert data['counts'][1]['query'] == base + 'gal=4T1'
        grid = {'grid': [('C_4', [
            {'count': 1, 'query': base + 'gal=4T1&' + NO_SEARCH_QUERY},
            {'count': 2, 'query': base + 'gal=4T1&e=2'}])]}
        LFStats._suppress_null_links(grid)
        assert grid['grid'][0][1][0]['query'] == ''
        assert grid['grid'][0][1][1]['query'] == base + 'gal=4T1&e=2'

    def test_dynamic_stats_null_bucket(self):
        # A not-computed Galois group (3996 fields) cannot be expressed as a search, so
        # its statistics bucket is shown without a drill-down link -- clicking it must
        # not open an unfiltered search returning every field (LMFDB#6542 review).
        import re
        empty_link = re.compile(r"href='[^']*[?&][A-Za-z_]+=(?:&amp;|')")
        for col, param in [('galois_label', 'gal'), ('slopes', 'slopes'), ('hidden', 'hidden')]:
            L = self.tc.get('/padicField/dynamic_stats?col1=%s&proportions=none&search_type=DynStats' % col)
            assert L.status_code == 200
            dat = L.get_data(as_text=True)
            assert 'not computed' in dat                  # the null bucket is displayed...
            assert "?%s='" % param not in dat             # ...with no empty-parameter link
            assert empty_link.search(dat) is None         # no drill-down has an empty value
            assert '\x00' not in dat                       # the sentinel never leaks to output
        # Non-null buckets still link to a correctly-filtered search (12 cyclic quartics)
        L = self.tc.get('/padicField/dynamic_stats?p=2&n=4&col1=galois_label&proportions=none&search_type=DynStats')
        dat = L.get_data(as_text=True)
        assert 'gal=4T1' in dat and empty_link.search(dat) is None

    def test_field_page(self):
        L = self.tc.get('/padicField/11.6.4.2', follow_redirects=True)
        assert '11.2.3.4a1.1' in L.get_data(as_text=True)
        assert 'x^{2} + 7 x + 2' in L.get_data(as_text=True) # bad (not robust) test, but it's the best i was able to find...
        assert 'x^{3} + 44 t + 99' in L.get_data(as_text=True) # bad (not robust) test, but it's the best i was able to find...

    def test_global_splitting_models(self):
        # The first one will have to change if we compute a GSM for it
        L = self.tc.get('/padicField/163.1.8.7a1.2')
        assert 'not computed' in L.get_data(as_text=True)
        L = self.tc.get('/padicField/2.8.1.0a1.1')
        assert 'Does not exist' in L.get_data(as_text=True)

    def test_underlying_data(self):
        page = self.tc.get('/padicField/11.2.3.4a1.2').get_data(as_text=True)
        assert 'Underlying data' in page and 'data/11.2.3.4a1.2' in page

    def test_search_download(self):
        page = self.tc.get('/padicField/?Submit=gp&download=1&query=%7B%27p%27%3A+2%2C+%27n%27%3A+2%7D&n=2&p=2').get_data(as_text=True)
        assert '''columns = ["label", "coeffs", "p", "f", "e", "c", "gal", "slopes"];
data = {[
["2.2.1.0a1.1", [1, 1, 1], 2, 2, 1, 0, [2, 1], [[], 1, 2]],
["2.1.2.2a1.1", [2, 2, 1], 2, 1, 2, 2, [2, 1], [[2], 1, 1]],
["2.1.2.2a1.2", [6, 2, 1], 2, 1, 2, 2, [2, 1], [[2], 1, 1]],
["2.1.2.3a1.1", [2, 0, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]],
["2.1.2.3a1.2", [10, 0, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]],
["2.1.2.3a1.3", [2, 4, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]],
["2.1.2.3a1.4", [10, 4, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]]
]};

create_record(row) =
{
    out = Map(["label",row[1];"coeffs",row[2];"p",row[3];"f",row[4];"e",row[5];"c",row[6];"gal",row[7];"slopes",row[8]]);
    field = Polrev(mapget(out, "coeffs"));
    mapput(~out, "field", field);
    return(out);''' in page

    def test_families_search_download(self):
        # Absolute families: download should produce a file (not just refresh the page).  Issue #6829.
        r = self.tc.get('/padicField/?Submit=sage&download=1&query=%7B%27n0%27%3A+1%2C+%27p%27%3A+2%2C+%27n%27%3A+2%7D&p=2&n=2&search_type=Families')
        assert 'attachment' in r.headers.get('Content-Disposition', '')
        page = r.get_data(as_text=True)
        assert '"2.2.1.0a"' in page
        assert '"2.1.2.2a"' in page
        # Relative families: download should also work and include the base field label.
        r = self.tc.get('/padicField/?Submit=sage&download=1&query=%7B%27base%27%3A+%272.2.1.0a1.1%27%2C+%27n%27%3A+2%7D&n=2&base=2.2.1.0a1.1&relative=1&search_type=Families')
        assert 'attachment' in r.headers.get('Content-Disposition', '')
        page = r.get_data(as_text=True)
        assert '"2.2.1.0a1.1"' in page
