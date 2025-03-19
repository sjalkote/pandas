# Note! This file is aimed specifically at pandas.io.formats.printing utility
# functions, not the general printing of pandas objects.
from collections.abc import Mapping
import string

import pytest

import pandas._config.config as cf

import pandas as pd

from pandas.io.formats import printing


@pytest.mark.parametrize(
    "input_names, expected_names",
    [
        (["'a b"], "['\\'a b']"),  # Escape leading quote
        (["test's b"], "['test\\'s b']"),  # Escape apostrophe
        (["'test' b"], "['\\'test\\' b']"),  # Escape surrounding quotes
        (["test b'"], "['test b\\'']"),  # Escape single quote
        (["test\n' b"], "['test\\n\\' b']"),  # Escape quotes, preserve newline
    ],
)
def test_formatted_index_names(input_names, expected_names):
    # GH#60190
    df = pd.DataFrame({name: [1, 2, 3] for name in input_names}).set_index(input_names)
    formatted_names = str(df.index.names)

    assert formatted_names == expected_names


def test_adjoin():
    data = [["a", "b", "c"], ["dd", "ee", "ff"], ["ggg", "hhh", "iii"]]
    expected = "a  dd  ggg\nb  ee  hhh\nc  ff  iii"

    adjoined = printing.adjoin(2, *data)

    assert adjoined == expected


class MyMapping(Mapping):
    def __getitem__(self, key):
        return 4

    def __iter__(self):
        return iter(["a", "b"])

    def __len__(self):
        return 2


class TestPPrintThing:
    def test_repr_binary_type(self):
        letters = string.ascii_letters
        try:
            raw = bytes(letters, encoding=cf.get_option("display.encoding"))
        except TypeError:
            raw = bytes(letters)
        b = str(raw.decode("utf-8"))
        res = printing.pprint_thing(b, quote_strings=True)
        assert res == repr(b)
        res = printing.pprint_thing(b, quote_strings=False)
        assert res == b

    def test_repr_obeys_max_seq_limit(self):
        with cf.option_context("display.max_seq_items", 2000):
            assert len(printing.pprint_thing(list(range(1000)))) > 1000

        with cf.option_context("display.max_seq_items", 5):
            assert len(printing.pprint_thing(list(range(1000)))) < 100

        with cf.option_context("display.max_seq_items", 1):
            assert len(printing.pprint_thing(list(range(1000)))) < 9

    def test_repr_set(self):
        assert printing.pprint_thing({1}) == "{1}"

    def test_repr_dict(self):
        assert printing.pprint_thing({"a": 4, "b": 4}) == "{'a': 4, 'b': 4}"

    def test_repr_mapping(self):
        assert printing.pprint_thing(MyMapping()) == "{'a': 4, 'b': 4}"

    def test_repr_frozenset(self):
        assert printing.pprint_thing(frozenset([1, 2])) == "frozenset({1, 2})"


class TestFormatBase:
    def test_adjoin(self):
        data = [["a", "b", "c"], ["dd", "ee", "ff"], ["ggg", "hhh", "iii"]]
        expected = "a  dd  ggg\nb  ee  hhh\nc  ff  iii"

        adjoined = printing.adjoin(2, *data)

        assert adjoined == expected

    def test_adjoin_unicode(self):
        data = [["あ", "b", "c"], ["dd", "ええ", "ff"], ["ggg", "hhh", "いいい"]]
        expected = "あ  dd  ggg\nb  ええ  hhh\nc  ff  いいい"
        adjoined = printing.adjoin(2, *data)
        assert adjoined == expected

        adj = printing._EastAsianTextAdjustment()

        expected = """あ  dd    ggg
b   ええ  hhh
c   ff    いいい"""

        adjoined = adj.adjoin(2, *data)
        assert adjoined == expected
        cols = adjoined.split("\n")
        assert adj.len(cols[0]) == 13
        assert adj.len(cols[1]) == 13
        assert adj.len(cols[2]) == 16

        expected = """あ       dd         ggg
b        ええ       hhh
c        ff         いいい"""

        adjoined = adj.adjoin(7, *data)
        assert adjoined == expected
        cols = adjoined.split("\n")
        assert adj.len(cols[0]) == 23
        assert adj.len(cols[1]) == 23
        assert adj.len(cols[2]) == 26

    def test_justify(self):
        adj = printing._EastAsianTextAdjustment()

        def just(x, *args, **kwargs):
            # wrapper to test single str
            return adj.justify([x], *args, **kwargs)[0]

        assert just("abc", 5, mode="left") == "abc  "
        assert just("abc", 5, mode="center") == " abc "
        assert just("abc", 5, mode="right") == "  abc"
        assert just("abc", 5, mode="left") == "abc  "
        assert just("abc", 5, mode="center") == " abc "
        assert just("abc", 5, mode="right") == "  abc"

        assert just("パンダ", 5, mode="left") == "パンダ"
        assert just("パンダ", 5, mode="center") == "パンダ"
        assert just("パンダ", 5, mode="right") == "パンダ"

        assert just("パンダ", 10, mode="left") == "パンダ    "
        assert just("パンダ", 10, mode="center") == "  パンダ  "
        assert just("パンダ", 10, mode="right") == "    パンダ"

    def test_east_asian_len(self):
        adj = printing._EastAsianTextAdjustment()

        assert adj.len("abc") == 3
        assert adj.len("abc") == 3

        assert adj.len("パンダ") == 6
        assert adj.len("ﾊﾟﾝﾀﾞ") == 5
        assert adj.len("パンダpanda") == 11
        assert adj.len("ﾊﾟﾝﾀﾞpanda") == 10

    def test_ambiguous_width(self):
        adj = printing._EastAsianTextAdjustment()
        assert adj.len("¡¡ab") == 4

        with cf.option_context("display.unicode.ambiguous_as_wide", True):
            adj = printing._EastAsianTextAdjustment()
            assert adj.len("¡¡ab") == 6

        data = [["あ", "b", "c"], ["dd", "ええ", "ff"], ["ggg", "¡¡ab", "いいい"]]
        expected = "あ  dd    ggg \nb   ええ  ¡¡ab\nc   ff    いいい"
        adjoined = adj.adjoin(2, *data)
        assert adjoined == expected
