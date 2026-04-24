import re
from typing import TypedDict

DANGEROUS_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above)",
    r"you are now",
    r"pretend (you are|to be)",
    r"system prompt:",
    r"new instructions:",
]


class _DetectResponse(TypedDict):
    is_suspicious: bool
    sanitized: str


def detect_prompt_injection(input: str) -> _DetectResponse:
    """Detect prompt injection in the input string."""
    sanitized = input
    is_suspicious = False

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, input, re.IGNORECASE):
            is_suspicious = True
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)

    return _DetectResponse(is_suspicious=is_suspicious, sanitized=sanitized)
