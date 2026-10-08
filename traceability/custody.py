#### created by Diego G. Salas, 2026-10-08
#
# Chain of custody for cord-blood units, from collection to cryostorage.
# Tables (see docs/custody_scheme.md):
#   units.tsv            din, check, donor_id, consent_id, collection_site
#   events.tsv           event_id, din, step, timestamp, location, from_custodian, to_custodian, signed_by
#   temperature_log.tsv  din, phase, timestamp, temp_c
# Every rule returns one row per unit, so a unit is traceable only if it passes all of them.
from collections import defaultdict
from datetime import datetime

from traceability import isbt128

STEPS = ["collection", "packaging", "courier_pickup", "lab_receipt",
         "processing", "cryopreservation", "storage"]
RULES = {
    "R1_identifier": "DIN well formed and ISO 7064 check character correct",
    "R2_donor_link": "unit linked to a donor pseudonym and a consent record; DIN unique",
    "R3_steps": "every required step recorded once, in order, with non-decreasing timestamps",
    "R4_handoff": "custody unbroken (giver = previous receiver) and every hand-off signed",
    "R5_transport_temp": "fresh-unit transport readings inside the SOP range",
    "R6_storage_temp": "cryostorage readings at or below the storage limit",
    "R7_time_to_processing": "collection to processing within the time limit",
    "R8_orphan_events": "every event refers to a registered unit",
}


def _ts(value):
    return datetime.fromisoformat(value)


def validate(units, events, temps, transport_min=15.0, transport_max=25.0,
             storage_max=-150.0, max_hours=48.0):
    """Return report rows: din, rule, status (pass|fail), detail."""
    by_unit = defaultdict(list)
    for ev in events:
        by_unit[ev["din"]].append(ev)
    temps_by_unit = defaultdict(list)
    for t in temps:
        temps_by_unit[t["din"]].append(t)
    din_counts = defaultdict(int)
    for u in units:
        din_counts[u["din"]] += 1

    report = []

    def add(din, rule, problems):
        report.append({"din": din, "rule": rule,
                       "status": "fail" if problems else "pass",
                       "detail": "; ".join(problems)})

    for u in units:
        din = u["din"]
        evs = sorted(by_unit.get(din, []), key=lambda e: _ts(e["timestamp"]))
        steps = [e["step"] for e in evs]

        ##### R1 identifier
        problems = []
        if not isbt128.is_well_formed(din):
            problems.append("malformed DIN")
        elif isbt128.check_character(din) != u["check"]:
            problems.append(f"check character {u['check']} != {isbt128.check_character(din)}")
        add(din, "R1_identifier", problems)

        ##### R2 donor link
        problems = []
        if not u["donor_id"]:
            problems.append("no donor pseudonym")
        if not u["consent_id"]:
            problems.append("no consent record")
        if din_counts[din] > 1:
            problems.append("DIN registered more than once")
        add(din, "R2_donor_link", problems)

        ##### R3 steps: once each, in order (events are already sorted by time)
        problems = [f"missing {s}" for s in STEPS if s not in steps]
        problems += [f"{s} recorded {steps.count(s)} times" for s in STEPS if steps.count(s) > 1]
        present = [s for s in steps if s in STEPS]
        if not problems and present != STEPS:
            problems.append("steps out of order: " + " > ".join(present))
        add(din, "R3_steps", problems)

        ##### R4 hand-off: giver must be the previous receiver; changes of custody signed
        problems = []
        for prev, cur in zip(evs, evs[1:]):
            if cur["from_custodian"] != prev["to_custodian"]:
                problems.append(f"{cur['step']}: from {cur['from_custodian']} but held by {prev['to_custodian']}")
        for ev in evs:
            if ev["from_custodian"] != ev["to_custodian"] and not ev["signed_by"]:
                problems.append(f"{ev['step']}: hand-off not signed")
        add(din, "R4_handoff", problems)

        ##### R5 / R6 temperature
        transport = [t for t in temps_by_unit[din] if t["phase"] == "transport"]
        storage = [t for t in temps_by_unit[din] if t["phase"] == "storage"]
        problems = [f"{t['timestamp']} {t['temp_c']} C" for t in transport
                    if not transport_min <= float(t["temp_c"]) <= transport_max]
        if not transport:
            problems.append("no transport log")
        add(din, "R5_transport_temp", problems)
        problems = [f"{t['timestamp']} {t['temp_c']} C" for t in storage
                    if float(t["temp_c"]) > storage_max]
        if "storage" in steps and not storage:
            problems.append("no storage log")
        add(din, "R6_storage_temp", problems)

        ##### R7 time to processing
        problems = []
        times = {e["step"]: _ts(e["timestamp"]) for e in evs}
        if "collection" in times and "processing" in times:
            hours = (times["processing"] - times["collection"]).total_seconds() / 3600
            if hours > max_hours:
                problems.append(f"{hours:.1f} h > {max_hours:g} h")
        else:
            problems.append("collection or processing not recorded")
        add(din, "R7_time_to_processing", problems)

    ##### R8 orphan events: refer to a DIN that is not registered
    registered = set(din_counts)
    for din in sorted(set(by_unit) - registered):
        add(din, "R8_orphan_events", [f"{len(by_unit[din])} events for unregistered DIN"])
    return report


def summarise(report):
    """Units checked, units traceable end to end, and failures per rule."""
    units = sorted({r["din"] for r in report if r["rule"] != "R8_orphan_events"})
    failing = {r["din"] for r in report if r["status"] == "fail" and r["rule"] != "R8_orphan_events"}
    rows = [{"metric": "units_checked", "value": len(units)},
            {"metric": "units_traceable", "value": len(units) - len(failing)},
            {"metric": "units_with_breaks", "value": len(failing)}]
    for rule in RULES:
        rows.append({"metric": f"fail_{rule}",
                     "value": sum(r["rule"] == rule and r["status"] == "fail" for r in report)})
    return rows


def trace(din, units, events, temps):
    """Plain-text history of one unit: donor, every event, temperature range per phase."""
    unit = next((u for u in units if u["din"] == din), None)
    if unit is None:
        return f"{din}: not registered"
    lines = [f"Unit {din} {unit['check']}  donor {unit['donor_id'] or '-'}  "
             f"consent {unit['consent_id'] or '-'}  site {unit['collection_site']}"]
    for ev in sorted((e for e in events if e["din"] == din), key=lambda e: _ts(e["timestamp"])):
        lines.append(f"  {ev['timestamp']}  {ev['step']:<17} {ev['location']:<16} "
                     f"{ev['from_custodian']} -> {ev['to_custodian']}  signed: {ev['signed_by'] or 'NO'}")
    for phase in ("transport", "storage"):
        vals = [float(t["temp_c"]) for t in temps if t["din"] == din and t["phase"] == phase]
        if vals:
            lines.append(f"  {phase} log: {len(vals)} readings, {min(vals):.1f} to {max(vals):.1f} C")
    return "\n".join(lines)
