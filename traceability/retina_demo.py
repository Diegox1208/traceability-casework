#### created by Diego G. Salas
#
# SYNTHETIC retinal-screening exams attached to anonymised patients.
# The public encounter data carry no images or grades, so the exams are generated,
# with known faults seeded for the QC checks to find. The grade distribution is
# illustrative, not an estimate of real prevalence.
import random

from traceability.qc import referable

DEVICES = ["handheld-A", "desktop-B", "smartphone-adapter-C"]
GRADES = ["0"] * 70 + ["1"] * 12 + ["2"] * 10 + ["3"] * 5 + ["4"] * 3
##### Rule -> number of exams broken on purpose
SEEDED = {"X1_patient_exists": 5, "X2_laterality": 4, "X3_grade_vs_quality": 6,
          "X4_referable_flag": 7, "X5_one_exam_per_eye": 3}


def make(patients, n_patients=500, seed=2026):
    rng = random.Random(seed)
    chosen = rng.sample([p["patient_pid"] for p in patients], min(n_patients, len(patients)))
    exams = []
    for pid in chosen:
        for eye in ("L", "R"):
            gradable = rng.random() > 0.08
            grade = rng.choice(GRADES) if gradable else ""
            dme = "yes" if gradable and grade in ("3", "4") and rng.random() < 0.5 else "no"
            exams.append({"exam_id": f"X{len(exams) + 1:05d}", "patient_pid": pid, "eye": eye,
                          "exam_month": f"2026-{rng.randrange(1, 10):02d}",
                          "device": rng.choice(DEVICES),
                          "image_quality": "gradable" if gradable else "ungradable",
                          "icdr_grade": grade, "dme": dme,
                          "referable": "yes" if gradable and referable(grade, dme) else "no"})

    ##### Seed faults on distinct exams (each exam gets at most one fault)
    pool = rng.sample(range(len(exams)), sum(SEEDED.values()))
    truth = []
    for rule, n in SEEDED.items():
        for _ in range(n):
            x = exams[pool.pop()]
            if rule == "X1_patient_exists":
                x["patient_pid"] = f"P{len(truth):016x}"        # unknown, and unique per fault
            elif rule == "X2_laterality":
                x["eye"] = "B"
            elif rule == "X3_grade_vs_quality":
                x.update(image_quality="gradable", icdr_grade="5", referable="yes")
            elif rule == "X4_referable_flag":
                x.update(image_quality="gradable", icdr_grade="0", dme="no", referable="yes")
            elif rule == "X5_one_exam_per_eye":
                dup = dict(x, exam_id=f"X{len(exams) + 1:05d}")
                exams.append(dup)
                truth.append({"exam_id": dup["exam_id"], "rule": rule})
            truth.append({"exam_id": x["exam_id"], "rule": rule})
    return exams, truth
