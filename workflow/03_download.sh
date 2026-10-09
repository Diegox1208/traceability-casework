#!/usr/bin/env bash
#### created by Diego G. Salas
#
# Stage 03 downloads the UCI "Diabetes 130-US hospitals for years 1999-2008" dataset
# (CC BY 4.0, DOI 10.24432/C5230J) and checks it against the recorded SHA-256.
set -euo pipefail

#---- ##-- Configuration ----
source "${CONFIG:-config/config.sh}"

##### Set variables
stage="03_download"
zipFile="${rawDir}/uci_diabetes.zip"

#---- ##-- Download once, verify every time ----
mkdir -p "${rawDir}"
if [[ ! -s "${zipFile}" ]]; then
  echo "[${stage}] downloading ${uciUrl}" >&2
  curl -sSL --fail -o "${zipFile}" "${uciUrl}"
fi

got="$(sha256sum "${zipFile}" | cut -d' ' -f1)"
if [[ "${got}" != "${uciSha256}" ]]; then
  echo "[${stage}] SHA-256 mismatch: expected ${uciSha256}, got ${got}" >&2
  echo "[${stage}] the source file changed; update uciSha256 in the config only after checking why" >&2
  exit 1
fi
unzip -o -q "${zipFile}" diabetic_data.csv -d "${rawDir}"
echo "[${stage}] ${zipFile} verified (sha256 ${got:0:12}...)"
