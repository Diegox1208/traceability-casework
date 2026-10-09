#!/usr/bin/env bash
#### created by Diego G. Salas
#
# Settings for run.sh. Every threshold the validators apply lives here.

##### Environment
python="${PYTHON:-python}"
date_="$(date +%Y-%m-%d)"

##### Paths
demoDir="data/demo/custody"
cacheDir="data/cache/worldbank"
rawDir="data/raw"
outDir="data/anonymised"
resultsDir="results"
logFile="${resultsDir}/run_log.tsv"

##### 01 chain of custody
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
uciSha256="f82ac129da2ddd2299391ff6fbae3a6a58b3edcf59ac9d7bd480c00fe453112a"
kAnonymity=5
ageWidth=20
examPatients=500
seed=2026
