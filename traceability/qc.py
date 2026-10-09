#### created by Diego G. Salas
#
# Quality-control checks on the anonymised patient-record tables.
# Runs after pseudonymisation, so the examples in the report never show a raw identifier.
import re
from collections import Counter

ICD9 = re.compile(r"^(V\d{2}|E\d{3}|\d{3})(\.\d{1,2})?$")
A1C_VALUES = {"None", "Norm", ">7", ">8", ""}
AGE_BAND = re.compile(r"^\[\d+-\d+\)$")


def _rule(table, rule, description, rows, failed_ids):
    return {"table": table, "rule": rule, "description": description, "n_checked": len(rows),
            "n_failed": len(failed_ids), "examples": ",".join(failed_ids[:3]),
            "failed_ids": failed_ids}


REPORT_FIELDS = ["table", "rule", "description", "n_checked", "n_failed", "examples"]


def check_records(patients, encounters):
    out = []
    dup = [e for e, n in Counter(e["encounter_pid"] for e in encounters).items() if n > 1]
    out.append(_rule("encounters", "Q1_unique_encounter", "encounter identifier is unique",
                     encounters, dup))
    out.append(_rule("patients", "Q2_sex_valid", "sex is Female or Male", patients,
                     [p["patient_pid"] for p in patients if p["sex"] not in ("Female", "Male")]))
    out.append(_rule("patients", "Q3_ethnicity_recorded", "ethnicity is recorded (not '?')", patients,
                     [p["patient_pid"] for p in patients if p["ethnicity"] in ("?", "")]))
    out.append(_rule("patients", "Q4_age_band_format", "age band looks like [a-b)", patients,
                     [p["patient_pid"] for p in patients if not AGE_BAND.match(p["age_band"])]))
    out.append(_rule("encounters", "Q5_length_of_stay", "time in hospital between 1 and 14 days",
                     encounters, [e["encounter_pid"] for e in encounters
                                  if not 1 <= int(e["time_in_hospital"]) <= 14]))
    out.append(_rule("encounters", "Q6_primary_diagnosis", "primary diagnosis recorded",
                     encounters, [e["encounter_pid"] for e in encounters if e["diag_1"] in ("?", "")]))
    out.append(_rule("encounters", "Q7_icd9_format", "recorded diagnoses are valid ICD-9 codes",
                     encounters, [e["encounter_pid"] for e in encounters
                                  if any(e[d] not in ("?", "") and not ICD9.match(e[d])
                                         for d in ("diag_1", "diag_2", "diag_3"))]))
    out.append(_rule("encounters", "Q7b_icd9_leading_zero",
                     "invalid code is a 1-2 digit number: leading zeros lost (038 stored as 38), "
                     "repairable by zero-padding", encounters,
                     [e["encounter_pid"] for e in encounters
                      if any(re.fullmatch(r"\d{1,2}", e[d]) for d in ("diag_1", "diag_2", "diag_3"))]))
    out.append(_rule("encounters", "Q8_a1c_value", "HbA1c result uses the coded values",
                     encounters, [e["encounter_pid"] for e in encounters
                                  if e["a1c_result"] not in A1C_VALUES]))
    known = {p["patient_pid"] for p in patients}
    out.append(_rule("encounters", "Q9_patient_exists", "encounter refers to a known patient",
                     encounters, [e["encounter_pid"] for e in encounters if e["patient_pid"] not in known]))
    return out


def referable(grade, dme):
    """ICDR moderate or worse (grade >= 2) or diabetic macular oedema."""
    return (grade != "" and int(grade) >= 2) or dme == "yes"


def check_exams(exams, patients):
    known = {p["patient_pid"] for p in patients}
    keys = Counter((x["patient_pid"], x["eye"], x["exam_month"]) for x in exams)
    out = [
        _rule("retinal_exams", "X1_patient_exists", "exam refers to a known patient", exams,
              [x["exam_id"] for x in exams if x["patient_pid"] not in known]),
        _rule("retinal_exams", "X2_laterality", "eye is L or R", exams,
              [x["exam_id"] for x in exams if x["eye"] not in ("L", "R")]),
        _rule("retinal_exams", "X3_grade_vs_quality",
              "gradable image has ICDR grade 0-4; ungradable image has no grade", exams,
              [x["exam_id"] for x in exams if not (
                  (x["image_quality"] == "gradable" and x["icdr_grade"] in list("01234")) or
                  (x["image_quality"] == "ungradable" and x["icdr_grade"] == ""))]),
        _rule("retinal_exams", "X4_referable_flag", "referable flag matches grade and DME", exams,
              [x["exam_id"] for x in exams if x["icdr_grade"] in list("01234") and
               (x["referable"] == "yes") != referable(x["icdr_grade"], x["dme"])]),
        _rule("retinal_exams", "X5_one_exam_per_eye", "one exam per patient, eye and month", exams,
              [x["exam_id"] for x in exams if keys[(x["patient_pid"], x["eye"], x["exam_month"])] > 1]),
    ]
    return out
