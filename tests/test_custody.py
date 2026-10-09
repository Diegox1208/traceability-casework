from traceability import custody, custody_demo


def _failures(report):
    return {(r["din"], r["rule"]) for r in report if r["status"] == "fail"}


def test_recovers_exactly_the_seeded_faults():
    units, events, temps, truth = custody_demo.make()
    report = custody.validate(units, events, temps)
    assert _failures(report) == {(t["din"], t["rule"]) for t in truth}


def test_clean_unit_is_traceable_end_to_end():
    units, events, temps, _ = custody_demo.make()
    clean = units[0]["din"]
    rows = [r for r in custody.validate(units, events, temps) if r["din"] == clean]
    assert len(rows) == 7 and all(r["status"] == "pass" for r in rows)
    history = custody.trace(clean, units, events, temps)
    for step in custody.STEPS:
        assert step in history


def test_broken_handoff_chain_is_caught():
    units, events, temps, _ = custody_demo.make()
    din = units[0]["din"]
    receipt = next(e for e in events if e["din"] == din and e["step"] == "lab_receipt")
    receipt["from_custodian"] = "COURIER-99"
    fails = _failures(custody.validate(units, events, temps))
    assert (din, "R4_handoff") in fails


def test_thresholds_come_from_arguments():
    units, events, temps, _ = custody_demo.make()
    report = custody.validate(units, events, temps, storage_max=-195.0)
    assert sum(r["rule"] == "R6_storage_temp" and r["status"] == "fail" for r in report) == len(units)


def test_summary_counts():
    units, events, temps, _ = custody_demo.make()
    summary = {r["metric"]: r["value"] for r in custody.summarise(custody.validate(units, events, temps))}
    assert summary["units_checked"] == 12
    assert summary["units_traceable"] == 5
    assert summary["units_with_breaks"] == 7
