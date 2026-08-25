#!/usr/bin/env python3
"""Inject the language switcher + hreflang alternates into a Kiln site page.
Idempotent: running it twice produces the same file."""
import re, pathlib, sys

BASE = "https://guptatushar10397.github.io/kiln-site"
# code -> (native name, url segment)   '' segment == site root == English
LOCALES = [
    ("en",      "English",             ""),
    ("de",      "Deutsch",             "de"),
    ("es",      "Español",             "es"),
    ("fr",      "Français",            "fr"),
    ("it",      "Italiano",            "it"),
    ("pt-BR",   "Português (Brasil)",  "pt-BR"),
    ("zh-Hans", "简体中文",              "zh-Hans"),
    ("ja",      "日本語",                "ja"),
    ("ko",      "한국어",                "ko"),
]
# The switcher label per locale ("Language" in that language)
LABEL = {"en":"Language","de":"Sprache","es":"Idioma","fr":"Langue","it":"Lingua",
         "pt-BR":"Idioma","zh-Hans":"语言","ja":"言語","ko":"언어"}

def alternates(page):
    out = []
    for code, _, seg in LOCALES:
        href = f"{BASE}/{seg + '/' if seg else ''}{page}"
        out.append(f'<link rel="alternate" hreflang="{code}" href="{href}">')
    out.append(f'<link rel="alternate" hreflang="x-default" href="{BASE}/{page}">')
    return "\n".join(out)

def switcher(page, current):
    """Depth-aware RELATIVE links: portable across hosts and testable locally."""
    at_root = current == "en"
    up = "" if at_root else "../"
    items = []
    for code, name, seg in LOCALES:
        # the page you are already on links to itself bare, not via ../<self>/
        href = page if code == current else f"{up}{seg + '/' if seg else ''}{page}"
        cur = ' aria-current="true"' if code == current else ""
        items.append(f'      <a href="{href}" hreflang="{code}" lang="{code}"{cur}>{name}</a>')
    return ('    <details class="lang">\n'
            f'      <summary>{LABEL[current]}</summary>\n'
            '      <div class="lang-menu">\n'
            + "\n".join(items) + "\n"
            '      </div>\n'
            '    </details>')

def canonical_url(page, locale):
    seg = dict((c, sg) for c, _, sg in LOCALES)[locale]
    return f"{BASE}/{seg + '/' if seg else ''}{page}"

def apply(path, page, locale):
    s = pathlib.Path(path).read_text(encoding="utf-8")
    url = canonical_url(page, locale)
    # canonical: rewrite if present, else insert just before the hreflang block
    if re.search(r'<link rel="canonical"[^>]*>', s):
        s = re.sub(r'<link rel="canonical"[^>]*>', f'<link rel="canonical" href="{url}">', s, count=1)
    else:
        s = s.replace("<!-- hreflang -->", f'<link rel="canonical" href="{url}">\n\n<!-- hreflang -->', 1)
    # og:url only where the page already carries Open Graph tags
    s = re.sub(r'<meta property="og:url" content="[^"]*">',
               f'<meta property="og:url" content="{url}">', s, count=1)
    # 1. lang attribute
    s = re.sub(r'<html lang="[^"]*">', f'<html lang="{locale}">', s, count=1)
    # 2. hreflang block — replace if present, else insert before </head>
    block = "<!-- hreflang -->\n" + alternates(page) + "\n<!-- /hreflang -->"
    if "<!-- hreflang -->" in s:
        s = re.sub(r"<!-- hreflang -->.*?<!-- /hreflang -->", block, s, flags=re.S)
    else:
        s = s.replace("<link rel=\"stylesheet\"", block + "\n\n<link rel=\"stylesheet\"", 1)
    # 3. switcher — replace if present, else append inside .nav-links
    sw = switcher(page, locale)
    if '<details class="lang">' in s:
        s = re.sub(r'    <details class="lang">.*?    </details>', sw, s, flags=re.S)
    else:
        s = re.sub(r'(\n  </div>\n</div></nav>)', "\n" + sw + r'\1', s, count=1)
    pathlib.Path(path).write_text(s, encoding="utf-8")
    return len(s)

if __name__ == "__main__":
    path, page, locale = sys.argv[1], sys.argv[2], sys.argv[3]
    print(f"  {path}: {apply(path, page, locale)} bytes")
