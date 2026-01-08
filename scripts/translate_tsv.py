#!/usr/bin/env python3
import argparse
import csv
import os
import random
import sys
import time
from typing import List, Optional

import requests

from placeholders import mask_placeholders, placeholders_match, restore_placeholders

DEFAULT_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
MAX_CHARS_PER_REQUEST = 9000
DEFAULT_BATCH_SIZE = 8
DEFAULT_SLEEP_BETWEEN_BATCHES = 1.0
DEFAULT_MAX_RETRIES = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate TSV source column to Ukrainian.")
    parser.add_argument("--in", dest="input_path", required=True)
    parser.add_argument("--out", dest="output_path", required=True)
    parser.add_argument("--from-lang", default="en")
    parser.add_argument("--to-lang", default="uk")
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def post_with_retry(
    url: str,
    headers: dict,
    payload: list,
    timeout: int = 60,
    params: Optional[dict] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> requests.Response:
    base_delay = 1.0
    max_delay = 15.0
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=payload, timeout=timeout, params=params)
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = min(max_delay, base_delay * (2**attempt))
            else:
                delay = min(max_delay, base_delay * (2**attempt))
            delay += random.uniform(0, 0.5)
            time.sleep(delay)
            continue
        response.raise_for_status()
        return response
    response.raise_for_status()
    return response


def translate_batch(
    endpoint: str,
    key: str,
    region: str,
    from_lang: str,
    to_lang: str,
    texts: List[str],
    max_retries: int,
) -> List[str]:
    if not texts:
        return []
    url = f"{endpoint.rstrip('/')}/translate"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Ocp-Apim-Subscription-Region": region,
        "Content-Type": "application/json",
    }
    body = [{"text": text} for text in texts]
    params = {"api-version": "3.0", "from": from_lang, "to": to_lang}
    response = post_with_retry(
        url,
        headers,
        body,
        timeout=60,
        max_retries=max_retries,
        params=params,
    )
    data = response.json()
    translations = []
    for item in data:
        if not item.get("translations"):
            translations.append("")
            continue
        translations.append(item["translations"][0]["text"])
    if len(translations) != len(texts):
        raise ValueError("Unexpected number of translations returned")
    return translations


def batched_indices(texts: List[str], batch_size: int) -> List[List[int]]:
    batches: List[List[int]] = []
    current: List[int] = []
    current_chars = 0
    for idx, text in enumerate(texts):
        length = len(text)
        if current and (len(current) >= batch_size or current_chars + length > MAX_CHARS_PER_REQUEST):
            batches.append(current)
            current = []
            current_chars = 0
        current.append(idx)
        current_chars += length
    if current:
        batches.append(current)
    return batches


def main() -> int:
    args = parse_args()
    key = os.getenv("AZURE_TRANSLATOR_KEY")
    region = os.getenv("AZURE_TRANSLATOR_REGION")
    endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT", DEFAULT_ENDPOINT)
    batch_size = args.batch_size or env_int("TRANSLATE_BATCH_SIZE", DEFAULT_BATCH_SIZE)
    sleep_between_batches = env_float("TRANSLATE_SLEEP", DEFAULT_SLEEP_BETWEEN_BATCHES)
    max_retries = env_int("TRANSLATE_MAX_RETRIES", DEFAULT_MAX_RETRIES)

    if not key or not region:
        print("ERROR: AZURE_TRANSLATOR_KEY and AZURE_TRANSLATOR_REGION must be set.", file=sys.stderr)
        return 1

    with open(args.input_path, "r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile, delimiter="\t")
        if not reader.fieldnames:
            print("ERROR: TSV header row is missing.", file=sys.stderr)
            return 1
        fieldnames = reader.fieldnames
        target_column = "translation" if "translation" in fieldnames else None
        if target_column is None and "translated" in fieldnames:
            target_column = "translated"
        if target_column is None:
            print("ERROR: Missing 'translation' or 'translated' column.", file=sys.stderr)
            return 1
        rows = list(reader)

    total_rows = len(rows)
    eligible_rows = 0
    translated_rows = 0
    skipped_rows = 0
    qa_failed = 0

    indices_to_translate: List[int] = []
    masked_sources: List[str] = []
    placeholder_lists: List[List[str]] = []

    for idx, row in enumerate(rows):
        source_text = (row.get("source") or "").strip()
        target_text = (row.get(target_column) or "").strip()
        if not source_text:
            skipped_rows += 1
            continue
        if target_text and not args.overwrite:
            skipped_rows += 1
            continue
        eligible_rows += 1
        masked, placeholders = mask_placeholders(source_text)
        indices_to_translate.append(idx)
        masked_sources.append(masked)
        placeholder_lists.append(placeholders)

    for batch in batched_indices(masked_sources, batch_size):
        batch_indices = [indices_to_translate[i] for i in batch]
        batch_masked = [masked_sources[i] for i in batch]
        batch_placeholders = [placeholder_lists[i] for i in batch]
        try:
            batch_translations = translate_batch(
                endpoint,
                key,
                region,
                args.from_lang.lower(),
                args.to_lang.lower(),
                batch_masked,
                max_retries,
            )
        except Exception as exc:
            print(f"ERROR: Translation batch failed: {exc}", file=sys.stderr)
            return 1

        for idx, masked_source, placeholders, masked_translation in zip(
            batch_indices, batch_masked, batch_placeholders, batch_translations
        ):
            if not placeholders_match(masked_source, masked_translation):
                qa_failed += 1
                continue
            restored = restore_placeholders(masked_translation, placeholders)
            rows[idx][target_column] = restored
            translated_rows += 1

        time.sleep(sleep_between_batches)

    output_path = args.output_path
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print("Translation summary")
    print(f"Total rows: {total_rows}")
    print(f"Eligible rows: {eligible_rows}")
    print(f"Translated: {translated_rows}")
    print(f"Skipped: {skipped_rows}")
    print(f"QA failed: {qa_failed}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
