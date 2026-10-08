#!/usr/bin/env bash
#### created by Diego G. Salas, 2026-10-08
#
# Runs the three cases end to end.
#   bash run.sh                    -> everything; downloads the public data on first run
#   OFFLINE=1 bash run.sh          -> register checked against the cached API responses only
#   DRY_RUN=1 bash run.sh          -> print every command, run nothing
#   PYTHON=.venv/bin/python bash run.sh
set -euo pipefail

#---- ##-- Configuration ----
export CONFIG="${CONFIG:-config/config.sh}"
DRY_RUN="${DRY_RUN:-0}"
OFFLINE="${OFFLINE:-0}"
source "${CONFIG}"

##### Build, log, run one stage
run_stage() {
  local stage="$1"; shift
  local cmd="$*"
  echo "[${stage}] ${cmd}"
  mkdir -p "${resultsDir}"
  echo -e "${stage}\t${cmd}\t${date_}" >> "${logFile}"
  if [[ "${DRY_RUN}" != "1" ]]; then
    eval "${cmd}"
  fi
}

offlineFlag=""
[[ "${OFFLINE}" == "1" ]] && offlineFlag="--offline"

#---- ##-- Stages ----
run_stage 01_custody "${python}" workflow/01_custody.py \
  --data-dir "${demoDir}" --results-dir "${resultsDir}" --units "${custodyUnits}" --seed "${seed}" \
  --transport-min "${transportMin}" --transport-max "${transportMax}" \
  --storage-max "${storageMax}" --max-hours "${maxHours}"

run_stage 02_register "${python}" workflow/02_register.py \
  --register "${register}" --cache-dir "${cacheDir}" --results-dir "${resultsDir}" \
  --country "${country}" --tolerance "${tolerance}" ${offlineFlag}

run_stage 03_download bash workflow/03_download.sh

run_stage 04_patient_records "${python}" workflow/04_patient_records.py \
  --raw "${rawDir}/diabetic_data.csv" --out-dir "${outDir}" --results-dir "${resultsDir}" \
  --k "${kAnonymity}" --age-width "${ageWidth}" --exam-patients "${examPatients}" --seed "${seed}"

echo "done: results in ${resultsDir}, log in ${logFile}"
