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

# The Google Fonts v1 CSS API serves a different font *format* depending on the
# requesting browser's User-Agent, and Qt's loader is picky about which it
# accepts: QFontDatabase.addApplicationFont rejects WOFF2 on the PyQt6 wheels
# (their bundled FreeType is built without WOFF2/brotli support) but always
# loads plain TrueType. So we send urllib's default agent first, which the API
# treats as an unknown browser and answers with .ttf; the modern Chrome agent
# (compact WOFF2) is kept only as a defensive fallback. Each candidate is
# verified with addApplicationFont, so correctness never depends on a particular
# agent or format -- we just keep the first download Qt can actually register.
# ``None`` means "send urllib's default User-Agent".
_USER_AGENTS = (
    None,
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)

# Font file URL inside the CSS, in any format Qt can load. We take the first
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


def _download_font(family, dest, user_agent):
    """Fetch a font file for ``family`` from Google Fonts into ``dest``.

    ``user_agent`` selects the format the CSS API serves (``None`` sends
    urllib's default agent and gets TTF; a modern agent gets WOFF2). Qt
    identifies fonts by their file contents, so the on-disk extension does not
    matter. Raises on a network/parse failure or an empty download.
    """
    # The CSS API expects spaces in family names encoded as ``+`` (e.g.
    # ``Open+Sans``); ``%20`` is rejected for multi-word families.
    css_url = "https://fonts.googleapis.com/css?family=" + urllib.parse.quote_plus(
        family
    )
    headers = {"User-Agent": user_agent} if user_agent else {}
    request = urllib.request.Request(css_url, headers=headers)
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


def _register(path):
    """Register the font file at ``path`` with Qt's application font database.

    Returns the family name Qt stored it under (which can differ from the Google
    Fonts name, e.g. "Roboto Condensed"), or ``None`` if Qt could not load the
    file -- for example a WOFF2 on a build whose FreeType lacks WOFF2 support.
    """
    font_id = QFontDatabase.addApplicationFont(str(path))
    if font_id == -1:
        return None
    families = QFontDatabase.applicationFontFamilies(font_id)
    return families[0] if families else None


def ensure_font(family):
    """Make ``family`` available to Qt, downloading + caching it if needed.

    Returns the family name to use when constructing a ``QFont`` (which may
    differ from ``family`` for downloaded fonts), or ``None`` if the font could
    not be made available. The returned name is one Qt has actually registered,
    so building a ``QFont`` with it won't silently fall back to a default family.
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
    # Trust an existing cache only if Qt can actually load it. A cache written by
    # an older build may hold a WOFF2 this Qt rejects, so fall through to a fresh
    # download (in a loadable format) when the cached file doesn't take.
    resolved = _register(cache) if cache.exists() else None
    if resolved is None:
        for user_agent in _USER_AGENTS:
            try:
                _download_font(family, cache, user_agent)
            except Exception as exc:  # noqa: BLE001 - best effort; try next agent
                print(f"[fonts] Could not download '{family}': {exc}",
                      file=sys.stderr)
                continue
            resolved = _register(cache)
            if resolved is not None:
                break
            # Qt rejected this format (e.g. WOFF2); discard it so the existence
            # check above won't pin us to it, then try the next agent/format.
            cache.unlink(missing_ok=True)

    if resolved is not None:
        _loaded[family] = resolved
        return resolved
    print(f"[fonts] Qt could not load any available format for '{family}'",
          file=sys.stderr)
    return None
