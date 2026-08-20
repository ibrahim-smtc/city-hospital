"""Discover URLs from cytecare.com sitemap. Warm cookies via homepage, then fetch XML with context.request."""
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path(__file__).parent / "discovery"
OUT_DIR.mkdir(exist_ok=True)

INDEX = "https://cytecare.com/sitemap_index.xml"
HOME = "https://cytecare.com/"


def extract_locs(xml: str):
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def warm_up(page):
    """Load homepage and wait until Anubis challenge redirects to real content."""
    page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            title = page.title()
        except Exception:
            time.sleep(0.5)
            continue
        if "Checking your browser" not in title:
            break
        time.sleep(0.5)
    # settle
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    print(f"  homepage title after warmup: {page.title()!r}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()

        print("Warming up (solving Anubis on homepage)...")
        warm_up(page)

        api = ctx.request  # inherits cookies

        print("Fetching sitemap index via context.request ...")
        resp = api.get(INDEX)
        idx_xml = resp.text()
        (OUT_DIR / "sitemap_index.xml").write_text(idx_xml, encoding="utf-8")
        print(f"  status={resp.status}  bytes={len(idx_xml)}")

        sub_sitemaps = extract_locs(idx_xml)
        print(f"Found {len(sub_sitemaps)} sub-sitemaps")
        for s in sub_sitemaps:
            print(f"  - {s}")

        all_urls = {}
        for sm in sub_sitemaps:
            print(f"Fetching {sm} ...")
            try:
                r = api.get(sm)
                body = r.text()
            except Exception as e:
                print(f"  ! failed {sm}: {e}")
                continue
            name = sm.rsplit("/", 1)[-1].replace(".xml", "")
            (OUT_DIR / f"{name}.xml").write_text(body, encoding="utf-8")
            urls = extract_locs(body)
            all_urls[name] = urls
            print(f"    {name}: status={r.status}  {len(urls)} urls")

        (OUT_DIR / "urls.json").write_text(json.dumps(all_urls, indent=2), encoding="utf-8")
        flat = sorted({u for lst in all_urls.values() for u in lst if not u.endswith(".xml")})
        (OUT_DIR / "urls_flat.txt").write_text("\n".join(flat), encoding="utf-8")
        print(f"\nTotal unique page URLs: {len(flat)}")

        browser.close()


if __name__ == "__main__":
    main()
