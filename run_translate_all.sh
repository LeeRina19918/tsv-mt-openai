#!/usr/bin/env bash
set -euo pipefail

shopt -s nullglob
FILES=(input/*.tsv)

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No TSV files found in input/." >&2
  exit 1
fi

for file in "${FILES[@]}"; do
  bash run_translate.sh "$file"
done
