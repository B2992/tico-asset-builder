from __future__ import annotations

import re
from pathlib import Path


BRACKETED_TEXT = re.compile(r"[\[(].*?[\])]")
NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalized_name(value: str) -> str:
    lowered = value.lower()
    without_brackets = BRACKETED_TEXT.sub(" ", lowered)
    return NON_ALNUM.sub(" ", without_brackets).strip()


def normalized_stem(path: Path) -> str:
    return normalized_name(strip_compound_suffix(path.name))


def strip_compound_suffix(filename: str) -> str:
    lowered = filename.lower()
    for suffix in (".nkit.iso",):
        if lowered.endswith(suffix):
            return filename[: -len(suffix)]
    return Path(filename).stem

