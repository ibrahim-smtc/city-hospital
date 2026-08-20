"""Discover: enumerate every URL from cytecare.com sitemap index."""
import json
import re
from pathlib import Path

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}

INDEX = "https://cytecare.com/sitemap_index.xml"
OUT_DIR = Path(__file__).parent / "discovery"
OUT_DIR.mkdir(exist_ok=True)


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


def extract_locs(xml):
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def main():
    idx = get(INDEX)
    (OUT_DIR / "sitemap_index.xml").write_text(idx, encoding="utf-8")
    sub_sitemaps = extract_locs(idx)
    print(f"Found {len(sub_sitemaps)} sub-sitemaps:")
    for s in sub_sitemaps:
        print(f"  - {s}")

    all_urls = {}  # sitemap_name -> [urls]
    for sm in sub_sitemaps:
        try:
            body = get(sm)
        except Exception as e:
            print(f"  ! failed {sm}: {e}")
            continue
        name = sm.rsplit("/", 1)[-1].replace(".xml", "")
        (OUT_DIR / f"{name}.xml").write_text(body, encoding="utf-8")
        urls = extract_locs(body)
        # first entry is the sitemap itself in some formats; keep all page urls
        all_urls[name] = urls
        print(f"    {name}: {len(urls)} urls")

    (OUT_DIR / "urls.json").write_text(json.dumps(all_urls, indent=2), encoding="utf-8")
    flat = sorted({u for lst in all_urls.values() for u in lst if u != INDEX})
    (OUT_DIR / "urls_flat.txt").write_text("\n".join(flat), encoding="utf-8")
    print(f"\nTotal unique URLs: {len(flat)}")


if __name__ == "__main__":
    main()
