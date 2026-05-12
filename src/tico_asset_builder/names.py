from __future__ import annotations

import re
from pathlib import Path


BRACKETED_TEXT = re.compile(r"[\[(].*?[\])]")
NON_ALNUM = re.compile(r"[^a-z0-9]+")
TRAILING_ARTWORK_WORDS = frozenset({"art", "artwork", "boxart", "box", "cover", "covers", "front", "image", "scan"})
LEADING_ARTICLES = frozenset({"a", "an", "the"})


def normalized_name(value: str) -> str:
    lowered = value.lower()
    without_brackets = BRACKETED_TEXT.sub(" ", lowered)
    without_apostrophes = without_brackets.replace("'", "")
    words = NON_ALNUM.sub(" ", without_apostrophes).split()
    if words and words[0] in LEADING_ARTICLES:
        words = words[1:]
    while words and words[-1] in TRAILING_ARTWORK_WORDS:
        words = words[:-1]
    return " ".join(words)


def normalized_stem(path: Path) -> str:
    return normalized_name(strip_compound_suffix(path.name))


def strip_compound_suffix(filename: str) -> str:
    lowered = filename.lower()
    for suffix in (".nkit.iso",):
        if lowered.endswith(suffix):
            return filename[: -len(suffix)]
    return Path(filename).stem
