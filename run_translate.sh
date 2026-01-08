#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 input/FILE.tsv" >&2
  exit 1
fi

INPUT_PATH="$1"
BASENAME="$(basename "$INPUT_PATH" .tsv)"
OUTPUT_PATH="output/${BASENAME}.uk.tsv"

python3 -m pip install -r requirements.txt >/dev/null

python3 scripts/translate_tsv.py \
  --in "$INPUT_PATH" \
  --out "$OUTPUT_PATH"
