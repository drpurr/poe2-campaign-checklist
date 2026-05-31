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

# An old-ish User-Agent makes the Google Fonts CSS API serve plain TrueType
# (.ttf) files instead of WOFF2, which Qt can load directly.
_TTF_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 5.1; rv:6.0) Gecko/20100101 Firefox/6.0"
)

# Remember which families we've already registered this session.
_loaded = set()


def _cache_path(family):
    safe = re.sub(r"[^A-Za-z0-9]+", "_", family).strip("_")
    return FONTS_DIR / f"{safe}.ttf"


def _download_font(family, dest):
    """Fetch a TrueType file for ``family`` from Google Fonts into ``dest``."""
    css_url = "https://fonts.googleapis.com/css?family=" + urllib.parse.quote(
        family
    )
    request = urllib.request.Request(css_url, headers={"User-Agent": _TTF_USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        css = response.read().decode("utf-8", "replace")
    match = re.search(r"url\((https://[^)]+\.ttf)\)", css)
    if not match:
        raise ValueError(f"No TrueType URL found for '{family}'")
    font_url = match.group(1)
    with urllib.request.urlopen(font_url, timeout=15) as response:
        data = response.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def ensure_font(family):
    """Make ``family`` available to Qt, downloading + caching it if needed.

    Returns True if the font is registered (now or already), False otherwise.
    """
    if not family or family in _loaded:
        return family in _loaded
    # Already a font Qt knows about (e.g. installed system font)? Nothing to do.
    if family in QFontDatabase.families():
        _loaded.add(family)
        return True

    cache = _cache_path(family)
    try:
        if not cache.exists():
            _download_font(family, cache)
        font_id = QFontDatabase.addApplicationFont(str(cache))
        if font_id != -1:
            _loaded.add(family)
            return True
    except Exception as exc:  # noqa: BLE001 - best effort; fall back silently
        print(f"[fonts] Could not load '{family}': {exc}", file=sys.stderr)
    return False
