#!/usr/bin/env python3
"""Deterministic site checks (stdlib only). Exit code 1 on any failure.

  - every locale's index.html has the same element structure as the English
    template (tag, class, id, attribute names), ignoring text
  - every local href/src on every page resolves to a file
  - each page has <html lang> = its locale and 10 hreflang alternates
  - footnote anchors referenced by <sup class="fn"> exist
  - per-locale image weight stays under budget, and every <img> has width,
    height and non-empty alt
"""
import html.parser, pathlib, sys, urllib.parse

SITE = pathlib.Path(__file__).resolve().parent.parent
LOCALES = ["en", "de", "es", "fr", "it", "pt-BR", "zh-Hans", "ja", "ko"]
PAGES = ["index.html", "support.html", "privacy.html"]
IMG_BUDGET_KB = 1400
fail = []


class Walk(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.shape, self.links, self.imgs, self.ids, self.fnrefs = [], [], [], set(), []
        self.lang, self.hreflang = None, 0
        self._in_sup_fn = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "link" and a.get("rel") == "alternate" and "hreflang" in a:
            self.hreflang += 1
        # structure signature: skip <link rel=alternate> and the language menu
        # entries, which chrome.py generates per locale
        if not (tag == "link" and a.get("rel") == "alternate"):
            self.shape.append((tag, a.get("class"), a.get("id"), tuple(sorted(k for k in a if k not in ("aria-current",)))))
        if "id" in a:
            self.ids.add(a["id"])
        for k in ("href", "src"):
            if k in a:
                self.links.append(a[k])
        if tag == "img":
            self.imgs.append(a)
        if tag == "sup" and a.get("class") == "fn":
            self._in_sup_fn = True
        if tag == "a" and self._in_sup_fn and a.get("href", "").startswith("#"):
            self.fnrefs.append(a["href"][1:])

    def handle_endtag(self, tag):
        if tag == "sup":
            self._in_sup_fn = False


def parse(path):
    w = Walk()
    w.feed(path.read_text(encoding="utf-8"))
    return w


def page_path(loc, page):
    return SITE / page if loc == "en" else SITE / loc / page


# lang-menu <a> entries differ in href per locale but not in shape; the shape
# comparison only uses attribute NAMES, so they line up.
template = parse(page_path("en", "index.html")).shape

for loc in LOCALES:
    for page in PAGES:
        p = page_path(loc, page)
        if not p.exists():
            fail.append(f"{loc}/{page}: missing")
            continue
        w = parse(p)
        if w.lang != loc:
            fail.append(f"{loc}/{page}: <html lang={w.lang!r}>")
        if w.hreflang != 10:
            fail.append(f"{loc}/{page}: {w.hreflang} hreflang alternates (want 10)")
        for href in w.links:
            u = urllib.parse.urlparse(href)
            if u.scheme or href.startswith(("#", "mailto:")):
                if href.startswith("#") and href[1:] and href[1:] not in w.ids:
                    fail.append(f"{loc}/{page}: anchor {href} has no target")
                continue
            target = (p.parent / urllib.parse.unquote(u.path)).resolve()
            if not target.exists():
                fail.append(f"{loc}/{page}: broken link {href}")
        for ref in w.fnrefs:
            if ref not in w.ids:
                fail.append(f"{loc}/{page}: footnote #{ref} missing")
        for img in w.imgs:
            for k in ("width", "height"):
                if not img.get(k):
                    fail.append(f"{loc}/{page}: <img {img.get('src')}> lacks {k}")
            if not (img.get("alt") or "").strip():
                fail.append(f"{loc}/{page}: <img {img.get('src')}> empty alt")
        if page == "index.html" and loc != "en":
            if w.shape != template:
                for i, (x, y) in enumerate(zip(template, w.shape)):
                    if x != y:
                        fail.append(f"{loc}/index.html: structure differs at element {i}: en={x} {loc}={y}")
                        break
                else:
                    fail.append(f"{loc}/index.html: {len(w.shape)} elements vs {len(template)} in en")
    imgs = SITE / "assets" / "img" / loc
    kb = sum(f.stat().st_size for f in imgs.glob("*.jpg")) / 1024 if imgs.exists() else 0
    if kb > IMG_BUDGET_KB:
        fail.append(f"{loc}: images {kb:.0f} KB > {IMG_BUDGET_KB} KB budget")

if fail:
    print("\n".join(fail))
    sys.exit(1)
print(f"OK — {len(LOCALES)} locales × {len(PAGES)} pages: structure, links, lang, hreflang, footnotes, images")
