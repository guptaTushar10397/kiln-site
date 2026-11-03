#!/usr/bin/env python3
"""One-off (idempotent): bring the support/privacy pages' nav in line with the
redesigned home page — skip link, aria-current on the current page, nav
aria-label, and the Download pill — without touching page content."""
import pathlib, re, sys
SITE = pathlib.Path(__file__).resolve().parent.parent
DOWNLOAD = {"en":"Download","de":"Laden","es":"Descargar","fr":"Télécharger","it":"Scarica",
            "pt-BR":"Baixar","zh-Hans":"下载","ja":"ダウンロード","ko":"다운로드"}
SKIP = {"en":"Skip to content","de":"Zum Inhalt springen","es":"Saltar al contenido","fr":"Aller au contenu",
        "it":"Vai al contenuto","pt-BR":"Pular para o conteúdo","zh-Hans":"跳到内容","ja":"コンテンツへスキップ",
        "ko":"본문으로 건너뛰기"}
NAV_LABEL = {"en":"Main","de":"Hauptnavigation","es":"Principal","fr":"Principale","it":"Principale",
             "pt-BR":"Principal","zh-Hans":"主导航","ja":"メイン","ko":"주 메뉴"}
STORE = "https://apps.apple.com/app/id6784888925"

def upgrade(path, loc, page):
    s = path.read_text(encoding="utf-8")
    if 'class="nav-cta"' in s:
        return "already"
    s = s.replace('<nav class="nav"><div class="wrap">',
                  f'<a class="skip" href="#main">{SKIP[loc]}</a>\n<nav class="nav" aria-label="{NAV_LABEL[loc]}"><div class="wrap">', 1)
    s = re.sub(r'(\n    </details>\n  </div>\n)(</div></nav>)',
               rf'\1  <a class="nav-cta" href="{STORE}">{DOWNLOAD[loc]}</a>\n\2', s, count=1)
    s = s.replace(f'<a href="{page}">', f'<a href="{page}" aria-current="page">', 1)
    s = re.sub(r'<main class="page">', '<main class="page" id="main">', s, count=1)
    assert 'class="nav-cta"' in s and 'id="main"' in s, path
    path.write_text(s, encoding="utf-8")
    return "upgraded"

for loc in DOWNLOAD:
    d = SITE if loc == "en" else SITE / loc
    for page in ("support.html", "privacy.html"):
        print(f"{loc:8} {page:13} {upgrade(d / page, loc, page)}")
