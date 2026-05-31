"""Google Fonts support for the overlay.

Provides a curated list of popular Google Font families and lazily downloads
the font files on demand, registering them with Qt's font database so they can
be rendered. Downloaded fonts are cached in the per-user app-data folder
(``poe2-campaign-tracker/fonts``) so a
font is only fetched once. Everything degrades gracefully: if a font can't be
downloaded (e.g. no internet), Qt simply falls back to a default family.
"""

import re
import sys
import urllib.parse
import urllib.request

from PyQt6.QtGui import QFontDatabase

from app_state import DATA_DIR

# A curated selection of widely-used Google Fonts. Kept short on purpose so the
# dropdown stays manageable; users can still see the live preview as they pick.
GOOGLE_FONTS = [
    "Roboto",
    "Open Sans",
    "Lato",
    "Montserrat",
    "Oswald",
    "Raleway",
    "Poppins",
    "Merriweather",
    "Nunito",
    "Source Sans 3",
    "Roboto Condensed",
    "Roboto Slab",
    "PT Sans",
    "Noto Sans",
    "Ubuntu",
    "Inter",
    "Cinzel",
    "EB Garamond",
    "Spectral",
    "IM Fell English",
]

FONTS_DIR = DATA_DIR / "fonts"

# Qt 6's font database can load TrueType (.ttf), OpenType (.otf) and Web Open
# Font Format (.woff/.woff2) files directly, so we let the Google Fonts CSS API
# serve whatever modern format it prefers (normally compact WOFF2). A modern
# User-Agent is required: older agents make the API return formats we then have
# to special-case, and an agent that supports WOFF (e.g. Firefox 6) makes the
# API serve .woff URLs that a .ttf-only matcher would miss entirely.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Font file URL inside the CSS, in any format Qt can load. We prefer the first
# match the API returns for the requested family.
_FONT_URL_RE = re.compile(r"url\((https://[^)]+\.(?:woff2|woff|ttf|otf))\)")

# Map a requested family -> the family name Qt actually registered it under.
# (Downloaded fonts frequently expose an internal family name that differs from
# the Google Fonts API name, e.g. "Roboto Condensed".) We cache the resolved
# name so callers always build their QFont from a family Qt can match exactly.
_loaded = {}


def _cache_path(family):
    safe = re.sub(r"[^A-Za-z0-9]+", "_", family).strip("_")
    return FONTS_DIR / f"{safe}.font"


def _download_font(family, dest):
    """Fetch a font file for ``family`` from Google Fonts into ``dest``.

    Accepts any web font format Qt can load (WOFF2/WOFF/TTF/OTF). Qt identifies
    fonts by their file contents, so the on-disk extension does not matter.
    """
    # The CSS API expects spaces in family names encoded as ``+`` (e.g.
    # ``Open+Sans``); ``%20`` is rejected for multi-word families.
    css_url = "https://fonts.googleapis.com/css?family=" + urllib.parse.quote_plus(
        family
    )
    request = urllib.request.Request(css_url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        css = response.read().decode("utf-8", "replace")
    match = _FONT_URL_RE.search(css)
    if not match:
        raise ValueError(f"No downloadable font URL found for '{family}'")
    font_url = match.group(1)
    with urllib.request.urlopen(font_url, timeout=15) as response:
        data = response.read()
    if not data:
        raise ValueError(f"Empty font download for '{family}'")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def ensure_font(family):
    """Make ``family`` available to Qt, downloading + caching it if needed.

    Returns the family name to use when constructing a ``QFont`` (which may
    differ from ``family`` for downloaded fonts), or ``None`` if the font could
    not be made available. The returned name is what Qt actually registered, so
    building ``QFont`` with it avoids a silent fallback to a default family.
    """
    if not family:
        return None
    if family in _loaded:
        return _loaded[family]
    # Already a font Qt knows about (e.g. installed system font)? Nothing to do.
    if family in QFontDatabase.families():
        _loaded[family] = family
        return family

    cache = _cache_path(family)
    try:
        if not cache.exists():
            _download_font(family, cache)
        font_id = QFontDatabase.addApplicationFont(str(cache))
        if font_id == -1:
            # A previously cached file that Qt can't parse (e.g. a truncated or
            # otherwise corrupt download) would block this family forever, since
            # the existence check above skips re-downloading. Drop it and try a
            # fresh download once.
            cache.unlink(missing_ok=True)
            _download_font(family, cache)
            font_id = QFontDatabase.addApplicationFont(str(cache))
        if font_id != -1:
            registered = QFontDatabase.applicationFontFamilies(font_id)
            resolved = registered[0] if registered else family
            _loaded[family] = resolved
            return resolved
    except Exception as exc:  # noqa: BLE001 - best effort; fall back silently
        print(f"[fonts] Could not load '{family}': {exc}", file=sys.stderr)
    return None
