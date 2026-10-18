"""Message catalogs for server-rendered text.

Only German is shipped. ``resolve_locale`` falls back to it until another
catalog exists and a caller passes that locale.
"""

import json
from pathlib import Path

DEFAULT_LOCALE = "de"
_DIR = Path(__file__).resolve().parent
_cache: dict[str, dict] = {}


def resolve_locale(locale: str | None) -> str:
    if locale and (_DIR / f"{locale}.json").is_file():
        return locale
    return DEFAULT_LOCALE


def _catalog(locale: str) -> dict:
    locale = resolve_locale(locale)
    cached = _cache.get(locale)
    if cached is None:
        cached = json.loads((_DIR / f"{locale}.json").read_text(encoding="utf-8"))
        _cache[locale] = cached
    return cached


def _lookup(locale: str, key: str):
    node = _catalog(locale)
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _resolve(key: str, locale: str):
    locale = resolve_locale(locale)
    node = _lookup(locale, key)
    if node is None and locale != DEFAULT_LOCALE:
        node = _lookup(DEFAULT_LOCALE, key)
    if node is None:
        raise KeyError(key)
    return node


def t(key: str, *, locale: str = DEFAULT_LOCALE, **values) -> str:
    node = _resolve(key, locale)
    if not isinstance(node, str):
        raise KeyError(key)
    return node.format(**values) if values else node


def t_list(key: str, *, locale: str = DEFAULT_LOCALE, **values) -> list[str]:
    node = _resolve(key, locale)
    if not isinstance(node, list) or not all(isinstance(item, str) for item in node):
        raise KeyError(key)
    if not values:
        return list(node)
    return [item.format(**values) for item in node]


def message(key: str, *, locale: str = DEFAULT_LOCALE) -> dict | None:
    node = _lookup(resolve_locale(locale), key)
    if node is None and resolve_locale(locale) != DEFAULT_LOCALE:
        node = _lookup(DEFAULT_LOCALE, key)
    return node if isinstance(node, dict) else None
