"""
Internationalisation helper.
Loads JSON translation files from the i18n/ folder and exposes t().
"""

import json
from pathlib import Path

_SUPPORTED = {"en", "es"}
_I18N_DIR = Path(__file__).parent.parent / "i18n"
_cache: dict[str, dict] = {}


def _load(lang: str) -> dict:
    if lang not in _cache:
        path = _I18N_DIR / f"{lang}.json"
        with open(path, encoding="utf-8") as f:
            _cache[lang] = json.load(f)
    return _cache[lang]


def t(key: str, lang: str = "en", **kwargs) -> str:
    """Return the translated string for *key* in *lang*, falling back to English."""
    if lang not in _SUPPORTED:
        lang = "en"
    data = _load(lang)
    en_data = _load("en")
    text = data.get(key) or en_data.get(key, key)
    return text.format(**kwargs) if kwargs else text
