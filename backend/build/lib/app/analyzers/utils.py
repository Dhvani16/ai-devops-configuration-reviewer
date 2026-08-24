"""Small shared helpers for deterministic analyzers."""

import re


def find_line_number(content: str, pattern: str) -> int | None:
    """Return the first one-based line matching a case-insensitive regex."""
    expression = re.compile(pattern, re.IGNORECASE)
    for line_number, line in enumerate(content.splitlines(), start=1):
        if expression.search(line):
            return line_number
    return None
