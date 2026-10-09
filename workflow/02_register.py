#### created by Diego G. Salas
#
# Stage 02 verifies every figure of the register against its public source.
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from traceability import register, tsv

#---- ##-- Arguments ----
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--register", required=True)
p.add_argument("--cache-dir", required=True)
p.add_argument("--results-dir", required=True)
p.add_argument("--country", default="PER")
p.add_argument("--tolerance", type=float, default=0.05)
p.add_argument("--offline", action="store_true", help="use cached responses only")
args = p.parse_args()

#---- ##-- Verify, write ----
verified = register.verify(tsv.read(args.register), args.cache_dir, args.country,
                           args.tolerance, args.offline)
tsv.write(f"{args.results_dir}/register_verified.tsv", verified)
summary = register.summarise(verified, args.tolerance)
tsv.write(f"{args.results_dir}/register_summary.tsv", summary)
print("[02_register] " + ", ".join(f"{r['metric']} {r['value']}" for r in summary))
