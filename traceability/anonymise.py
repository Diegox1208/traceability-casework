#### created by Diego G. Salas, 2026-10-08
#
# Map raw encounter records (UCI "Diabetes 130-US hospitals" layout) into the patient-record
# data model of docs/patient_data_model.md and anonymise them:
#   1. pseudonymise identifiers with HMAC-SHA256 (key kept outside the repository)
#   2. keep only the fields the screening model needs (data minimisation)
#   3. generalise quasi-identifiers (age band, sex, ethnicity) and suppress the patients
#      whose combination is shared by fewer than k patients
import hashlib
import hmac
import os
import re
import secrets
import sys
from collections import Counter

QUASI_IDENTIFIERS = ("sex", "age_band", "ethnicity")
ENCOUNTER_FIELDS = ["encounter_pid", "patient_pid", "admission_type_id", "time_in_hospital",
                    "num_medications", "diag_1", "diag_2", "diag_3", "a1c_result",
                    "diabetes_med", "readmitted"]
DROPPED = ["weight", "payer_code", "medical_specialty"]   # not needed for screening


def load_key(env="TRACE_HMAC_KEY"):
    """Return (key, stable). Without the variable the key is random and lives only in memory,
    so pseudonyms cannot be linked across runs (stable = False)."""
    key = os.environ.get(env)
    if key:
        return key.encode(), True
    print(f"[anonymise] {env} not set: using a random key, pseudonyms will differ between runs",
          file=sys.stderr)
    return secrets.token_bytes(32), False


def pseudonym(key, prefix, value):
    return prefix + hmac.new(key, str(value).encode(), hashlib.sha256).hexdigest()[:16]


def widen_age(band, width=20):
    """'[70-80)' -> '[60-80)' for width 20; anything unparseable is returned unchanged."""
    m = re.fullmatch(r"\[(\d+)-(\d+)\)", band)
    if not m:
        return band
    lo = int(m.group(1)) // width * width
    return f"[{lo}-{lo + width})"


def k_min(patients):
    counts = Counter(tuple(p[q] for q in QUASI_IDENTIFIERS) for p in patients)
    return min(counts.values()) if counts else 0, counts


def to_model(raw_rows, key):
    """Raw encounter rows -> (patients, encounters). Patient attributes come from the
    patient's first encounter in file order."""
    patients, encounters = {}, []
    for r in raw_rows:
        pid = pseudonym(key, "P", r["patient_nbr"])
        if pid not in patients:
            patients[pid] = {"patient_pid": pid, "sex": r["gender"], "age_band": r["age"],
                             "ethnicity": r["race"]}
        encounters.append({
            "encounter_pid": pseudonym(key, "E", r["encounter_id"]), "patient_pid": pid,
            "admission_type_id": r["admission_type_id"], "time_in_hospital": r["time_in_hospital"],
            "num_medications": r["num_medications"], "diag_1": r["diag_1"], "diag_2": r["diag_2"],
            "diag_3": r["diag_3"], "a1c_result": r["A1Cresult"], "diabetes_med": r["diabetesMed"],
            "readmitted": r["readmitted"]})
    return list(patients.values()), encounters


def enforce_k(patients, encounters, k=5, width=20):
    """Generalise age bands, then suppress patients in classes smaller than k.
    Returns (patients, encounters, log rows)."""
    log = [{"step": "pseudonymised", "patients": len(patients), "encounters": len(encounters),
            "k_min": k_min(patients)[0]}]
    patients = [dict(p, age_band=widen_age(p["age_band"], width)) for p in patients]
    log.append({"step": f"age generalised to {width}-year bands", "patients": len(patients),
                "encounters": len(encounters), "k_min": k_min(patients)[0]})
    _, counts = k_min(patients)
    keep = [p for p in patients if counts[tuple(p[q] for q in QUASI_IDENTIFIERS)] >= k]
    kept_ids = {p["patient_pid"] for p in keep}
    encounters = [e for e in encounters if e["patient_pid"] in kept_ids]
    log.append({"step": f"classes with fewer than {k} patients suppressed", "patients": len(keep),
                "encounters": len(encounters), "k_min": k_min(keep)[0]})
    return keep, encounters, log
