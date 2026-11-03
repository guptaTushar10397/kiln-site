#!/usr/bin/env python3
"""Render the home page's device imagery for every site locale.

Inputs (dev machine): Kiln's localized raw screenshots and Apple's device
bezels. Output: assets/img/<site-locale>/*.jpg, committed with the site.

Usage: scripts/build_images.py [--screens DIR] [--bezels DIR] [locale ...]
Background colours must match the section each image sits in (style.css):
  --black #000000 (hero, reports, languages, mac)   --band #101012 (how, privacy, reminders)
"""
import argparse, os, pathlib, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
LOCALES = {  # site segment -> App Store Connect screenshot folder
    "en": "en-US", "de": "de-DE", "es": "es-ES", "fr": "fr-FR", "it": "it",
    "pt-BR": "pt-BR", "zh-Hans": "zh-Hans", "ja": "ja", "ko": "ko",
}
BLACK, BAND = "#000000", "#101012"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screens", default=os.path.expanduser("~/Personal_New/Kiln/scripts/screenshots/out"))
    ap.add_argument("--bezels", default=os.path.expanduser("~/Personal_New/Kiln Design Assets/bezels"))
    ap.add_argument("locales", nargs="*")
    a = ap.parse_args()
    binary = pathlib.Path(tempfile.gettempdir()) / "kiln_site_images"
    subprocess.run(["swiftc", "-O", str(HERE / "site_images.swift"), "-o", str(binary)], check=True)
    mac = f"{a.bezels}/macbook-pro-14-m5-space-black.png"
    phone = f"{a.bezels}/iphone-17-pro-max-silver.png"
    for site in (a.locales or LOCALES):
        src = f"{a.screens}/{LOCALES[site]}"
        out = SITE / "assets" / "img" / site
        jobs = [
            ["hero", f"{src}/mac/3-library.png", mac, f"{src}/iphone/4-transcript.png", phone,
             f"{out}/hero.jpg", "2400", "1340", BLACK],
            ["phone", f"{src}/iphone/6-record.png", phone, f"{out}/step-record.jpg", "760", BAND],
            ["phone", f"{src}/iphone/4-transcript.png", phone, f"{out}/step-transcript.jpg", "760", BAND],
            ["phone", f"{src}/iphone/5-outputs.png", phone, f"{out}/step-outputs.jpg", "760", BAND],
            ["phone", f"{src}/iphone/9-reminders.png", phone, f"{out}/reminders.jpg", "760", BAND],
            ["mac", f"{src}/mac/6-report.png", mac, f"{out}/mac-report.jpg", "2000", BLACK],
        ]
        for j in jobs:
            subprocess.run([str(binary), *j], check=True, stdout=subprocess.DEVNULL)
        size = sum(f.stat().st_size for f in out.glob("*.jpg"))
        print(f"{site:8} {len(jobs)} images  {size/1024:.0f} KB")

if __name__ == "__main__":
    main()
