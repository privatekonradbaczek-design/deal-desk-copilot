from __future__ import annotations

import re

INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(previous|prior|above|all)\s+instructions?", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"\[SYSTEM[:\s]", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a\s+)", re.IGNORECASE),
    re.compile(r"disregard\s+(previous|prior|above)", re.IGNORECASE),
    re.compile(r"override\s+(your\s+)?(instructions?|rules?|guidelines?)", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|to\s+be)", re.IGNORECASE),
    re.compile(r"</?(system|assistant|user|instruction)>", re.IGNORECASE),
]

PII_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),            # SSN (US)
    re.compile(r"\b\d{2}-\d{3}-\d{2}-\d{5}\b"),       # Polish PESEL
    re.compile(r"\b[A-Z]{2}\d{7}\b"),                  # Passport (simplified)
    re.compile(r"\b(?:\d[ -]?){13,16}\b"),             # Credit card (simplified)
]


class InjectionDetector:
    def __init__(self, score_threshold: float = 0.70) -> None:
        self._threshold = score_threshold

    def score(self, text: str) -> tuple[float, list[str]]:
        """Return (injection_score 0.0-1.0, matched_patterns)."""
        matches: list[str] = []
        for pattern in INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                matches.append(match.group(0))

        if not matches:
            return 0.0, []

        score = min(1.0, len(matches) * 0.35)
        return score, matches

    def is_injection(self, text: str) -> tuple[bool, float, list[str]]:
        score, matches = self.score(text)
        return score >= self._threshold, score, matches


class PIIDetector:
    def detect(self, text: str) -> list[str]:
        """Return list of detected PII pattern names."""
        detected = []
        for pattern in PII_PATTERNS:
            if pattern.search(text):
                detected.append(pattern.pattern)
        return detected
