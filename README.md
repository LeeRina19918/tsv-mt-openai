# tsv-auto-translate-azure

Super-simple TSV machine translation for game localization using Azure Translator.

## What this does

- Reads **only** the `source` column in your TSV.
- Writes translations **only** into the `translation` column (or `translated` if `translation` is missing).
- Preserves all other columns exactly as-is.
- Output goes to `output/*.uk.tsv` with the same row order/count.

## Quick start (Codespaces)

1. Put your TSV files in `input/`.
2. Copy `.env.example` to `.env` and fill in `AZURE_TRANSLATOR_KEY` and `AZURE_TRANSLATOR_REGION`.
3. Run:

```bash
bash run_translate_all.sh
```

Or for a single file:

```bash
bash run_translate.sh input/example.tsv
```

## Example TSV (tiny)

```tsv
id\tflags\tsource\ttranslation
1\tui\tStart Game\t
2\tui\tOptions\t
```

## Quick test on a smaller file

```bash
head -n 200 input/uk.tsv > input/uk_small.tsv
bash run_translate.sh input/uk_small.tsv
```

## Troubleshooting

- **Missing columns**: the TSV must have a header row and include `source` plus `translation` or `translated`.
- **Missing key/region**: set `AZURE_TRANSLATOR_KEY` and `AZURE_TRANSLATOR_REGION` before running the scripts.
- **QA failures**: if placeholder checks fail, that row is skipped and counted as `QA failed` in the summary.
- **429 throttling**: the tool retries automatically with backoff. If Azure keeps throttling, try tuning in `.env`:
  - `TRANSLATE_BATCH_SIZE=10`
  - `TRANSLATE_SLEEP=0.5`
  Note: F0 quota errors (like `403001`) are different from 429.

## Commands

- One file:
  ```bash
  bash run_translate.sh input/example.tsv
  ```
  Output: `output/example.uk.tsv`
- All files:
  ```bash
  bash run_translate_all.sh
  ```
  Output: `output/*.uk.tsv`
