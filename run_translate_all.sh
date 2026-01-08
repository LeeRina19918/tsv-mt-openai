#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

shopt -s nullglob
FILES=(input/*.tsv)

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No TSV files found in input/." >&2
  exit 1
fi

for file in "${FILES[@]}"; do
  bash run_translate.sh "$file"
done
