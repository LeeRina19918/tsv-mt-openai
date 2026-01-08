import re
from typing import List, Tuple

PLACEHOLDER_PATTERN = re.compile(
    r"(\\[nt])"  # escaped sequences
    r"|(%[A-Z][A-Z0-9_]+)"  # macro-ish percent tokens
    r"|(%[-+0-9.#]*[a-zA-Z])"  # printf tokens
    r"|(\{[^}]+\})"  # brace tokens
    r"|(<[^>]+>)"  # XML/HTML tags
)

PH_RE = re.compile(r"__PH\d+__")


def mask_placeholders(text: str) -> Tuple[str, List[str]]:
    placeholders: List[str] = []

    def repl(match: re.Match) -> str:
        placeholders.append(match.group(0))
        return f"__PH{len(placeholders) - 1}__"

    masked = PLACEHOLDER_PATTERN.sub(repl, text)
    return masked, placeholders


def restore_placeholders(text: str, placeholders: List[str]) -> str:
    for idx, token in enumerate(placeholders):
        text = text.replace(f"__PH{idx}__", token)
    return text


def placeholders_match(masked_source: str, masked_translation: str) -> bool:
    return PH_RE.findall(masked_source) == PH_RE.findall(masked_translation)
