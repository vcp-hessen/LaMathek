"""Every error code the API can return has a German text in the web client."""

import json
import re
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1] / "lamathek"
LOCALE = Path(__file__).resolve().parents[2] / "web" / "src" / "locales" / "de.json"

_PATTERNS = (
    r'ValueError\("([a-z_]+)"\)',
    r'"error":\s*"([a-z_]+)"',
    r'AvailabilityError\("([a-z_]+)"',
    r'ImpersonationError\("([a-z_]+)"\)',
)


def _codes() -> set[str]:
    codes: set[str] = set()
    for path in SERVER.rglob("*.py"):
        if "migrations" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in _PATTERNS:
            codes |= set(re.findall(pattern, text))
    return codes


def test_every_api_error_code_has_a_german_text():
    messages = json.loads(LOCALE.read_text(encoding="utf-8"))
    known = (
        set(messages["errors"])
        | set(messages["loans"]["errors"])
        | set(messages["material"]["errors"])
    )
    assert sorted(_codes() - known) == []
