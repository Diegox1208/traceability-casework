#!/usr/bin/env bash
#### created by Diego G. Salas
#
# Settings for run.sh. Every threshold the validators apply lives here.

##### Environment
python="${PYTHON:-python}"
date_="$(date +%Y-%m-%d)"

##### Paths
demoDir="data/demo/custody"        # synthetic custody records (committed)
cacheDir="data/cache/worldbank"    # raw API responses with their SHA-256 (committed)
rawDir="data/raw"                  # downloaded public data (not committed)
outDir="data/anonymised"           # anonymised tables (not committed)
resultsDir="results"
logFile="${resultsDir}/run_log.tsv"

##### 01 chain of custody
# NetCord-FACT sets cryostorage at or below -150 C and collection to processing within 48 h.
# Fresh-unit transport range is set by each bank's SOP, and 15-25 C is a demonstration value.
custodyUnits=12
transportMin=15
transportMax=25
storageMax=-150
maxHours=48

##### 02 verification register
register="register/register_demo.tsv"
country="PER"
tolerance=0.05

##### 03-04 patient records
uciUrl="https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip"
uciSha256="f82ac129da2ddd2299391ff6fbae3a6a58b3edcf59ac9d7bd480c00fe453112a"   # SHA-256 of the file as first downloaded
kAnonymity=5
ageWidth=20
examPatients=500
seed=2026
