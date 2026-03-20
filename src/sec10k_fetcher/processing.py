from __future__ import annotations

import re
from dataclasses import dataclass


SECTION_ALIASES = {
    "business": "business",
    "item 1": "business",
    "risk_factors": "risk_factors",
    "risk factors": "risk_factors",
    "item 1a": "risk_factors",
    "mda": "mda",
    "md&a": "mda",
    "management discussion and analysis": "mda",
    "item 7": "mda",
    "financials": "financials",
    "financial statements": "financials",
    "item 8": "financials",
}

SECTION_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "business": (
        re.compile(r"^#+\s*(item\s*1[\s\.:_-]|business)\b", re.IGNORECASE),
    ),
    "risk_factors": (
        re.compile(r"^#+\s*(item\s*1a[\s\.:_-]|risk factors)\b", re.IGNORECASE),
    ),
    "mda": (
        re.compile(
            r"^#+\s*(item\s*7[\s\.:_-]|management[^\n]{0,80}discussion[^\n]{0,80}analysis)\b",
            re.IGNORECASE,
        ),
    ),
    "financials": (
        re.compile(r"^#+\s*(item\s*8[\s\.:_-]|financial statements)\b", re.IGNORECASE),
    ),
}


@dataclass
class Chunk:
    chunk_id: str
    section: str
    text: str


def normalize_sections(sections: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in sections:
        key = SECTION_ALIASES.get(item.strip().lower(), item.strip().lower())
        if key and key in SECTION_PATTERNS and key not in normalized:
            normalized.append(key)
    return normalized


def extract_sections(markdown: str, wanted_sections: list[str]) -> dict[str, str]:
    if not wanted_sections:
        return {"full": markdown}

    lines = markdown.splitlines()
    matches: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        for section in wanted_sections:
            patterns = SECTION_PATTERNS.get(section, ())
            if any(pattern.search(line) for pattern in patterns):
                matches.append((index, section))
                break

    if not matches:
        return {"full": markdown}

    matches.sort(key=lambda item: item[0])
    sections: dict[str, str] = {}
    for idx, (start, section) in enumerate(matches):
        end = matches[idx + 1][0] if idx + 1 < len(matches) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        if body:
            sections[section] = body
    return sections or {"full": markdown}


def chunk_text(section: str, text: str, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    if len(text) <= chunk_size:
        return [Chunk(chunk_id=f"{section}_0001", section=section, text=text)]

    chunks: list[Chunk] = []
    step = chunk_size - chunk_overlap
    start = 0
    index = 1
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk_text_value = text[start:end]
        chunks.append(Chunk(chunk_id=f"{section}_{index:04d}", section=section, text=chunk_text_value))
        if end == len(text):
            break
        start += step
        index += 1
    return chunks
