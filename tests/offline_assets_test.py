"""The offline guarantee.

The app must make **zero external requests** at runtime. Two reasons, both real:

  1. The handheld build (ROG Ally) has to work with no network at all — a car
     ride, a plane, a dead router. A CDN `<link>` in `index.html` turns a
     working app into unstyled text.
  2. Privacy: a font fetch tells a third party every time someone opens the app.

`tools/vendor_fonts.py` bundles the fonts into `static/fonts/` (SIL OFL, so
redistribution is permitted). This test stops a CDN reference creeping back in —
which is easy to do, since pasting a Google Fonts snippet is the normal way to
add a typeface.
"""
import os
import re

import pytest

STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "static")

#: Hosts that would mean a runtime request off-box.
FORBIDDEN = ("fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net",
             "unpkg.com", "cdnjs.cloudflare.com", "ajax.googleapis.com")


def _served_files():
    """Every file the browser actually loads (not docs, not prose)."""
    for root, _dirs, files in os.walk(STATIC):
        for name in files:
            if name.endswith((".html", ".css", ".js")):
                yield os.path.join(root, name)


def test_no_cdn_hosts_in_loadable_references():
    """No src=/href= pointing at a CDN. Prose links in credits are fine."""
    offenders = []
    for path in _served_files():
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        # only attribute references and CSS url()/@import actually fetch
        for m in re.finditer(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']'
                             r'|url\(\s*["\']?([^)"\']+)', text):
            ref = m.group(1) or m.group(2) or ""
            if any(host in ref for host in FORBIDDEN):
                offenders.append(f"{os.path.relpath(path, STATIC)}: {ref}")
    assert not offenders, "external asset requests found:\n  " + "\n  ".join(offenders)


def test_fonts_css_exists_and_is_local():
    css = os.path.join(STATIC, "css", "fonts.css")
    assert os.path.isfile(css), "run: python3 tools/vendor_fonts.py"
    with open(css, encoding="utf-8") as fh:
        text = fh.read()
    refs = re.findall(r'url\(\s*["\']?(/fonts/[^)"\']+)', text)
    assert refs, "fonts.css declares no local font files"
    for ref in refs:
        assert os.path.isfile(os.path.join(STATIC, ref.lstrip("/"))), f"missing {ref}"


def test_index_loads_the_local_font_stylesheet():
    index = os.path.join(STATIC, "index.html")
    with open(index, encoding="utf-8") as fh:
        html = fh.read()
    assert "/css/fonts.css" in html


@pytest.mark.parametrize("family", ["VT323", "Pixelify Sans", "Cinzel",
                                    "Crimson Text", "Space Mono",
                                    "Atkinson Hyperlegible"])
def test_every_family_the_css_uses_is_bundled(family):
    """A family referenced by the stylesheets must actually ship."""
    with open(os.path.join(STATIC, "css", "fonts.css"), encoding="utf-8") as fh:
        assert family in fh.read(), f"{family} is not vendored"
