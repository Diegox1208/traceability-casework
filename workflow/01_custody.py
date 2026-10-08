#### created by Diego G. Salas, 2026-10-08
#
# Stage 01: generate the synthetic cord-blood custody records and validate them.
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from traceability import custody, custody_demo, tsv  # noqa: E402

#---- ##-- Arguments ----
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--data-dir", required=True)
p.add_argument("--results-dir", required=True)
p.add_argument("--units", type=int, default=12)
p.add_argument("--seed", type=int, default=2026)
p.add_argument("--transport-min", type=float, default=15.0)
p.add_argument("--transport-max", type=float, default=25.0)
p.add_argument("--storage-max", type=float, default=-150.0)
p.add_argument("--max-hours", type=float, default=48.0)
args = p.parse_args()

#---- ##-- Generate, validate, write ----
units, events, temps, truth = custody_demo.make(args.units, args.seed)
tsv.write(f"{args.data_dir}/units.tsv", units)
tsv.write(f"{args.data_dir}/events.tsv", events)
tsv.write(f"{args.data_dir}/temperature_log.tsv", temps)
tsv.write(f"{args.data_dir}/seeded_faults.tsv", truth)

report = custody.validate(units, events, temps, args.transport_min, args.transport_max,
                          args.storage_max, args.max_hours)
tsv.write(f"{args.results_dir}/custody_report.tsv", report)
tsv.write(f"{args.results_dir}/custody_summary.tsv", custody.summarise(report))
with open(f"{args.results_dir}/custody_trace_example.txt", "w", encoding="utf-8", newline="\n") as fh:
    for u in (units[0], units[6]):                     # one clean unit, one with an excursion
        fh.write(custody.trace(u["din"], units, events, temps) + "\n\n")

##### Recovered faults vs seeded faults
found = {(r["din"], r["rule"]) for r in report if r["status"] == "fail"}
seeded = {(t["din"], t["rule"]) for t in truth}
print(f"[01_custody] seeded {len(seeded)}, detected {len(found & seeded)}, "
      f"missed {len(seeded - found)}, false alarms {len(found - seeded)}")
