import random

import pytest

from traceability import isbt128


def test_reference_value():
    assert isbt128.check_character("G123498654321") == "H"


def test_matches_independent_implementation():
    mod_37_2 = pytest.importorskip("stdnum.iso7064.mod_37_2")
    rng = random.Random(1)
    for _ in range(500):
        din = "".join(rng.choice(isbt128.ALPHABET[:36]) for _ in range(5)) + \
              "".join(rng.choice("0123456789") for _ in range(8))
        assert isbt128.check_character(din) == mod_37_2.calc_check_digit(din)


def test_detects_every_single_substitution():
    din = "Z999926000001"
    check = isbt128.check_character(din)
    for i in range(len(din)):
        for ch in "0123456789":
            if ch != din[i]:
                assert isbt128.check_character(din[:i] + ch + din[i + 1:]) != check


def test_detects_adjacent_transpositions():
    din = "Z999926123457"
    check = isbt128.check_character(din)
    for i in range(len(din) - 1):
        if din[i] != din[i + 1]:
            swapped = din[:i] + din[i + 1] + din[i] + din[i + 2:]
            assert isbt128.check_character(swapped) != check


def test_format():
    assert isbt128.is_valid("G123498654321", "H")
    assert not isbt128.is_well_formed("G12349865432")
    assert not isbt128.is_valid("G123498654321", "A")
