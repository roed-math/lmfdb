"""
Unit tests for search input parsing (lmfdb/utils/search_parsing.py),
focused on ranges with negative endpoints; see issue #3825.
"""

import pytest

from psycodict.utils import SearchParsingError

from lmfdb.app import app
from lmfdb.utils.search_parsing import (
    LIST_RE,
    LIST_FLOAT_RE,
    parse_floats,
    parse_ints,
    parse_ints_to_list,
    parse_range2,
    parse_range3,
    prep_ranges,
)


def test_prep_ranges():
    assert prep_ranges("2..10") == "2-10"
    assert prep_ranges("-4..-1") == "-4--1"
    assert prep_ranges("-1..3") == "-1-3"
    assert prep_ranges("..-4") == "--4"


def test_list_re():
    # prep_ranges has already replaced .. by - when LIST_RE is applied
    for ok in ["5", "-5", "5-10", "-1-3", "-4--1", "5-", "-5-", "--4",
               "-5,-2", "-4--1,7", "1--3"]:
        assert LIST_RE.match(ok), ok
    for bad in ["--", "3--", "---4", "2..10", "2+3", "1,,2", "x-2"]:
        assert not LIST_RE.match(bad), bad


def test_list_float_re():
    for ok in ["-1.5", "-1.5-2.5", "-4--1", "--4.5", "2.5-", "-2.5-", "1e-5",
               "1/4", "-1/4-1/2"]:
        assert LIST_FLOAT_RE.match(ok), ok
    for bad in ["--", "1.5--", "1..5"]:
        assert not LIST_FLOAT_RE.match(bad), bad


def test_parse_range2_signed():
    # a single leading - is a minus sign, not an open left endpoint
    assert parse_range2("-5", "c") == ["c", -5]
    assert parse_range2("-1-3", "c") == ["c", {"$gte": -1, "$lte": 3}]
    assert parse_range2("-4--1", "c") == ["c", {"$gte": -4, "$lte": -1}]
    assert parse_range2("--4", "c") == ["c", {"$lte": -4}]
    assert parse_range2("5-", "c") == ["c", {"$gte": 5}]
    assert parse_range2("-5-", "c") == ["c", {"$gte": -5}]
    assert parse_range2("-5,-2", "c") == ["$or", [{"c": -5}, {"c": -2}]]
    # .. ranges, as seen when the input is not preprocessed by prep_ranges
    assert parse_range2("-4..-1", "c") == ["c", {"$gte": -4, "$lte": -1}]
    assert parse_range2("..-4", "c") == ["c", {"$lte": -4}]
    assert parse_range2("..10", "c") == ["c", {"$lte": 10}]
    with pytest.raises(SearchParsingError):
        parse_range2("..", "c")


def test_parse_range3_signed():
    assert parse_range3("-4--1,2") == [[-4, -1], 2]
    assert parse_range3("-2-2", split0=True) == [[-2, -1], [1, 2]]


def test_parse_ints_to_list_signed():
    assert parse_ints_to_list("-4..-1") == [-4, -3, -2, -1]
    assert parse_ints_to_list("-1-3") == [-1, 0, 1, 2, 3]
    assert parse_ints_to_list("-5") == [-5]
    assert parse_ints_to_list("5-", max_val=7) == [5, 6, 7]


def test_parse_ints_negative_ranges():
    for inp, expected in [
        ("-5", -5),
        ("-1-3", {"$gte": -1, "$lte": 3}),
        ("-1..3", {"$gte": -1, "$lte": 3}),
        ("-4--1", {"$gte": -4, "$lte": -1}),
        ("-4..-1", {"$gte": -4, "$lte": -1}),
        ("..-4", {"$lte": -4}),
        ("-4..", {"$gte": -4}),
        ("2..10", {"$gte": 2, "$lte": 10}),
        ("5-", {"$gte": 5}),
    ]:
        query = {}
        parse_ints({"c": inp}, query, "c")
        assert query == {"c": expected}, inp
    query = {}
    parse_ints({"c": "-5,-2"}, query, "c")
    assert query == {"$or": [{"c": -5}, {"c": -2}]}
    query = {}
    parse_ints({"c": "-4--1,7"}, query, "c")
    assert query == {"$or": [{"c": {"$gte": -4, "$lte": -1}}, {"c": 7}]}
    # the input is echoed back in its preprocessed form
    info = {"c": "-4..-1"}
    parse_ints(info, {}, "c")
    assert info["c"] == "-4--1"


def test_parse_ints_invalid():
    app.config["TESTING"] = True
    if not app.secret_key:
        app.secret_key = "test_secret_key_for_testing_only"
    with app.test_request_context():
        for inp in ["3--", "1.5", "a-2"]:
            with pytest.raises(ValueError):
                parse_ints({"c": inp}, {}, "c")


def test_parse_floats_negative_ranges():
    query = {}
    parse_floats({"c": "-4..-1"}, query, "c")
    assert query["c"]["$gte"] == pytest.approx(-4, abs=1e-9)
    assert query["c"]["$lte"] == pytest.approx(-1, abs=1e-9)
    query = {}
    parse_floats({"c": "..-4.5"}, query, "c")
    assert set(query["c"]) == {"$lte"}
    assert query["c"]["$lte"] == pytest.approx(-4.5, abs=1e-9)
    query = {}
    parse_floats({"c": "-2.5-"}, query, "c")
    assert set(query["c"]) == {"$gte"}
    assert query["c"]["$gte"] == pytest.approx(-2.5, abs=1e-9)
    # scientific notation: the - after e is not a range separator
    query = {}
    parse_floats({"c": "1e-5"}, query, "c")
    assert query["c"]["$gte"] == pytest.approx(5e-6)
    assert query["c"]["$lte"] == pytest.approx(1.5e-5)
    query = {}
    parse_floats({"c": "1e-5-2e-4"}, query, "c")
    assert query["c"]["$gte"] == pytest.approx(1e-5, abs=1e-9)
    assert query["c"]["$lte"] == pytest.approx(2e-4, abs=1e-9)
