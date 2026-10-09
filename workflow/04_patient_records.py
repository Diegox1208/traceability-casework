#### created by Diego G. Salas
#
# Stage 04 maps public encounter records into the data model, anonymises them,
# attaches synthetic retinal exams and runs the quality-control checks.
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from traceability import anonymise, qc, retina_demo, tsv

#---- ##-- Arguments ----
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--raw", required=True, help="diabetic_data.csv")
p.add_argument("--out-dir", required=True, help="anonymised tables (never committed)")
p.add_argument("--results-dir", required=True)
p.add_argument("--k", type=int, default=5)
p.add_argument("--age-width", type=int, default=20)
p.add_argument("--exam-patients", type=int, default=500)
p.add_argument("--seed", type=int, default=2026)
args = p.parse_args()

#---- ##-- Map, anonymise ----
with open(args.raw, newline="", encoding="utf-8") as fh:
    raw = list(csv.DictReader(fh))
key, stable_key = anonymise.load_key()
patients, encounters = anonymise.to_model(raw, key)
del raw
qc_rows = qc.check_records(patients, encounters)
patients, encounters, log = anonymise.enforce_k(patients, encounters, args.k, args.age_width)

#---- ##-- Synthetic retinal exams, QC ----
exams, truth = retina_demo.make(patients, args.exam_patients, args.seed)
qc_rows += qc.check_exams(exams, patients)
if not stable_key:
    for r in qc_rows:
        if r["table"] != "retinal_exams" and r["examples"]:
            r["examples"] = "set TRACE_HMAC_KEY to list examples"

tsv.write(f"{args.out_dir}/patients.tsv", patients)
tsv.write(f"{args.out_dir}/encounters.tsv", encounters)
tsv.write(f"{args.out_dir}/retinal_exams.tsv", exams)
tsv.write(f"{args.results_dir}/anonymisation_log.tsv", log)
tsv.write(f"{args.results_dir}/qc_report.tsv", qc_rows, qc.REPORT_FIELDS)

tsv.write(f"{args.results_dir}/retinal_seeded_faults.tsv", truth)

##### Seeded exam faults vs QC findings (exact match is checked in tests/)
print(f"[04_patient_records] {log[0]['patients']} patients -> {log[-1]['patients']} after k>={args.k}; "
      f"k_min {log[0]['k_min']} -> {log[-1]['k_min']}; exam faults seeded {len(truth)}, "
      f"flagged {sum(r['n_failed'] for r in qc_rows if r['table'] == 'retinal_exams')}")
