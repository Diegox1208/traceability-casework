#### created by Diego G. Salas, 2026-10-08
#
# SYNTHETIC demonstration data for the chain-of-custody validator.
# No public chain-of-custody records for cord blood exist, so the units, people and
# readings below are generated. Facility code Z9999 is fictional. Each seeded fault
# is written to seeded_faults.tsv, the ground truth the validator must recover.
import random
from datetime import datetime, timedelta, timezone

from traceability import isbt128

LIMA = timezone(timedelta(hours=-5))
FACILITY, YEAR = "Z9999", "26"

##### Unit number -> (rule it must break, what is done to the data)
FAULTS = {
    2: ("R1_identifier", "check character mistyped on the label"),
    4: ("R2_donor_link", "consent record missing"),
    5: ("R4_handoff", "courier pick-up not signed"),
    7: ("R5_transport_temp", "transport excursion to 31.5 C"),
    9: ("R6_storage_temp", "storage reading of -120 C"),
    10: ("R7_time_to_processing", "processed 53 h after collection"),
    11: ("R3_steps", "packaging step never recorded"),
}
ORPHAN_DIN = f"{FACILITY}{YEAR}999999"


def make(n_units=12, seed=2026):
    rng = random.Random(seed)
    units, events, temps, truth = [], [], [], []
    for i in range(1, n_units + 1):
        din = f"{FACILITY}{YEAR}{i:06d}"
        check = isbt128.check_character(din)
        fault = FAULTS.get(i, (None, None))[0]
        if fault == "R1_identifier":
            check = isbt128.ALPHABET[(isbt128.ALPHABET.index(check) + 1) % 37]
        units.append({"din": din, "check": check, "donor_id": f"DON-{rng.randrange(16**6):06X}",
                      "consent_id": "" if fault == "R2_donor_link" else f"CNS-2026-{i:04d}",
                      "collection_site": rng.choice(["MAT-SITE-A", "MAT-SITE-B"])})
        if fault:
            truth.append({"din": din, "rule": fault, "fault": FAULTS[i][1]})

        ##### Timeline (hours after collection) and custodians
        t0 = datetime(2026, 9, 1, tzinfo=LIMA) + timedelta(days=rng.randrange(28),
                                                          hours=rng.randrange(6, 20))
        pickup = rng.uniform(1, 3)
        receipt = pickup + rng.uniform(2, 5)
        processing = 53.0 if fault == "R7_time_to_processing" else receipt + rng.uniform(1, 30)
        nurse, courier = f"NURSE-{rng.randrange(1, 4):02d}", f"COURIER-{rng.randrange(1, 3):02d}"
        tech = f"LABTECH-{rng.randrange(1, 4):02d}"
        plan = [
            ("collection", 0.0, units[-1]["collection_site"], "MOTHER", nurse),
            ("packaging", 0.5, units[-1]["collection_site"], nurse, nurse),
            ("courier_pickup", pickup, units[-1]["collection_site"], nurse, courier),
            ("lab_receipt", receipt, "PROCESSING-LAB", courier, tech),
            ("processing", processing, "PROCESSING-LAB", tech, tech),
            ("cryopreservation", processing + 2.0, "PROCESSING-LAB", tech, tech),
            ("storage", processing + 3.5, "LN2-TANK-A", tech, "LN2-TANK-A"),
        ]
        for step, hours, location, giver, receiver in plan:
            if fault == "R3_steps" and step == "packaging":
                continue
            signed = receiver if step == "collection" else giver     # the nurse signs the collection
            if fault == "R4_handoff" and step == "courier_pickup":
                signed = ""
            events.append({"event_id": f"EV-{len(events) + 1:04d}", "din": din, "step": step,
                           "timestamp": (t0 + timedelta(hours=hours)).isoformat(timespec="minutes"),
                           "location": location, "from_custodian": giver,
                           "to_custodian": receiver, "signed_by": signed})

        ##### Temperature logs: every 30 min in transport, daily for a week in storage
        h = pickup
        while h <= receipt:
            temps.append({"din": din, "phase": "transport",
                          "timestamp": (t0 + timedelta(hours=h)).isoformat(timespec="minutes"),
                          "temp_c": f"{rng.uniform(18, 24):.1f}"})
            h += 0.5
        if fault == "R5_transport_temp":
            temps[-1]["temp_c"] = "31.5"
        for day in range(1, 8):
            temps.append({"din": din, "phase": "storage",
                          "timestamp": (t0 + timedelta(hours=processing + 3.5, days=day)).isoformat(timespec="minutes"),
                          "temp_c": f"{rng.uniform(-196, -185):.1f}"})
        if fault == "R6_storage_temp":
            temps[-3]["temp_c"] = "-120.0"

    ##### One event for a unit that was never registered
    events.append({"event_id": f"EV-{len(events) + 1:04d}", "din": ORPHAN_DIN, "step": "lab_receipt",
                   "timestamp": "2026-09-15T10:00-05:00", "location": "PROCESSING-LAB",
                   "from_custodian": "COURIER-01", "to_custodian": "LABTECH-01", "signed_by": "COURIER-01"})
    truth.append({"din": ORPHAN_DIN, "rule": "R8_orphan_events", "fault": "event for an unregistered unit"})
    return units, events, temps, truth
