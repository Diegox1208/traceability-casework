from collections import defaultdict

from traceability import anonymise, qc, retina_demo

KEY = b"test-key"


def _raw(encounter_id, patient_nbr, gender="Female", age="[70-80)", race="Caucasian",
         diag_1="250.83", diag_2="?", diag_3="?", stay="3", a1c="None"):
    return {"encounter_id": str(encounter_id), "patient_nbr": str(patient_nbr), "race": race,
            "gender": gender, "age": age, "weight": "?", "payer_code": "MC",
            "medical_specialty": "Cardiology", "admission_type_id": "1", "time_in_hospital": stay,
            "num_medications": "10", "diag_1": diag_1, "diag_2": diag_2, "diag_3": diag_3,
            "A1Cresult": a1c, "diabetesMed": "Yes", "readmitted": "NO"}


def _population():
    rows = [_raw(1000 + i, 500 + i) for i in range(12)]
    rows += [_raw(2000 + i, 600 + i, gender="Male") for i in range(6)]
    rows.append(_raw(3000, 700, age="[40-50)"))
    rows.append(_raw(3001, 701, gender="Unknown/Invalid", diag_1="38", race="?"))
    rows.append(_raw(3002, 501, diag_1="?", stay="15"))
    return rows


def test_pseudonyms_are_keyed_and_hide_raw_ids():
    patients, encounters = anonymise.to_model(_population(), KEY)
    again, _ = anonymise.to_model(_population(), KEY)
    other, _ = anonymise.to_model(_population(), b"another-key")
    assert [p["patient_pid"] for p in patients] == [p["patient_pid"] for p in again]
    assert {p["patient_pid"] for p in patients}.isdisjoint({p["patient_pid"] for p in other})
    text = repr(patients) + repr(encounters)
    for raw_id in ("1000", "500", "3002"):
        assert f"'{raw_id}'" not in text
    for dropped in anonymise.DROPPED:
        assert all(dropped not in e for e in encounters)


def test_k_anonymity_is_enforced():
    patients, encounters = anonymise.to_model(_population(), KEY)
    kept, kept_enc, log = anonymise.enforce_k(patients, encounters, k=5)
    assert log[0]["k_min"] == 1 and log[-1]["k_min"] >= 5
    assert len(kept) == 18
    assert all(e["patient_pid"] in {p["patient_pid"] for p in kept} for e in kept_enc)


def test_widen_age():
    assert anonymise.widen_age("[70-80)") == "[60-80)"
    assert anonymise.widen_age("[90-100)") == "[80-100)"


def test_record_checks_find_the_planted_problems():
    patients, encounters = anonymise.to_model(_population(), KEY)
    failed = {r["rule"]: r["n_failed"] for r in qc.check_records(patients, encounters)}
    assert failed["Q2_sex_valid"] == 1
    assert failed["Q3_ethnicity_recorded"] == 1
    assert failed["Q5_length_of_stay"] == 1
    assert failed["Q6_primary_diagnosis"] == 1
    assert failed["Q7_icd9_format"] == 1 and failed["Q7b_icd9_leading_zero"] == 1
    assert failed["Q1_unique_encounter"] == failed["Q9_patient_exists"] == 0


def test_exam_checks_recover_exactly_the_seeded_faults():
    patients = [{"patient_pid": f"P{i:016x}", "sex": "Female", "age_band": "[60-80)",
                 "ethnicity": "Caucasian"} for i in range(1000, 1600)]
    exams, truth = retina_demo.make(patients, n_patients=500)
    found = {(i, r["rule"]) for r in qc.check_exams(exams, patients) for i in r["failed_ids"]}
    assert found == {(t["exam_id"], t["rule"]) for t in truth}
    per_rule = defaultdict(int)
    for t in truth:
        per_rule[t["rule"]] += 1
    assert per_rule["X5_one_exam_per_eye"] == 2 * retina_demo.SEEDED["X5_one_exam_per_eye"]
