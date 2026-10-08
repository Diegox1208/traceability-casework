import os

import pytest

from traceability import register, tsv

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "fixtures", "worldbank")
CLAIMS = os.path.join(HERE, "..", "register", "register_demo.tsv")


def _verified():
    return {r["claim_id"]: r for r in register.verify(tsv.read(CLAIMS), CACHE, offline=True)}


def test_demo_register_outcome():
    v = _verified()
    status = {k: r["status"] for k, r in v.items()}
    assert sum(s == "confirmed" for s in status.values()) == 9
    assert status["C07"] == "contradicted"                 # 2022 value quoted as 2023
    assert status["C11"] == status["C12"] == "unconfirmable"
    assert [k for k, r in v.items() if r["used_in_model"] == "no"] == ["C07", "C11", "C12"]


def test_every_checked_value_keeps_its_provenance():
    for r in _verified().values():
        if r["source_type"] == "worldbank":
            assert r["source_url"].startswith("https://api.worldbank.org/")
            assert len(r["sha256"]) == 64 and r["retrieved_at"]


def test_derived_value_uses_observed_inputs():
    c03 = _verified()["C03"]
    assert c03["status"] == "confirmed"
    assert abs(float(c03["observed_value"]) - 539635) < 1


def test_tolerance_changes_the_verdict():
    v = {r["claim_id"]: r for r in register.verify(tsv.read(CLAIMS), CACHE, tolerance=0.001, offline=True)}
    assert v["C01"]["status"] == "contradicted"            # 0.13 % off fails a 0.1 % tolerance


def test_missing_cache_offline_is_unconfirmable(tmp_path):
    claims = [{"claim_id": "C01", "claim": "x", "claimed_value": "1", "unit": "", "year": "2023",
               "source_type": "worldbank", "source_ref": "SP.POP.TOTL", "note": ""}]
    assert register.verify(claims, str(tmp_path), offline=True)[0]["status"] == "unconfirmable"


def test_expressions_are_restricted():
    with pytest.raises(ValueError):
        register._derive("__import__('os')", {})
