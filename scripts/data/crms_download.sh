#!/usr/bin/env bash
# Fetch the weekly CIMS continuous hydrographic export (CRMS + all CPRA projects).
# ~1.6 GB compressed; refreshed every Sunday. Keeps dated copies.
set -euo pipefail
DATA_ROOT="${DATA_ROOT:-/data/ywan245/subdomainLSTM/data}"
OUT="$DATA_ROOT/raw/CRMS"
mkdir -p "$OUT"
STAMP=$(date -u +%Y%m%d)
URL="https://cims.coastal.la.gov/RequestedDownloads/ZippedFiles/Full_Continuous_Hydrographic.zip"
curl -sSL --retry 5 --retry-delay 30 -o "$OUT/Full_Continuous_Hydrographic_$STAMP.zip.part" "$URL"
mv "$OUT/Full_Continuous_Hydrographic_$STAMP.zip.part" "$OUT/Full_Continuous_Hydrographic_$STAMP.zip"
ln -sfn "Full_Continuous_Hydrographic_$STAMP.zip" "$OUT/Full_Continuous_Hydrographic_latest.zip"
ls -la "$OUT"
unzip -l "$OUT/Full_Continuous_Hydrographic_latest.zip" | head -20
