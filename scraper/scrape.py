"""Scrape cytecare.com pages listed in discovery/urls.json into a categorized markdown KB."""
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
DISCOVERY = Path(__file__).parent / "discovery"
KB = ROOT / "kb"
SCRAPED_AT = "2026-08-20"

# URL prefix -> (folder, doc_type)
CATEGORY_MAP = [
    ("/our-cancer-specialist/", ("doctors", "doctor")),
    ("/team/", ("team", "team_member")),
    ("/treatment/", ("specialties", "specialty")),
    ("/cancer-diagnosis/", ("specialties", "diagnosis_service")),
    ("/support-services/", ("services", "support_service")),
    ("/health-clinics/", ("services", "clinic")),
]

# Sitemaps to draw from
INCLUDE_SITEMAPS = {
    "doctors-sitemap", "service-sitemap", "diagnosis-sitemap",
    "clinics-sitemap", "team-sitemap", "other-sitemap", "page-sitemap",
}

# Regex for pages under page-sitemap that are worth keeping (hospital info)
KEEP_PAGE_SLUGS = {
    "", "appointment", "contact-us", "about-us", "about", "our-hospital",
    "leadership", "why-cytecare", "prevention-screening", "cancer-support-services",
    "in-house-facilities", "international-patients", "insurance", "empanelment",
    "faqs", "faq", "career", "careers", "media-coverage",
    "cytecare-comprehensive-health-package-above-40",
    "cytecare-comprehensive-health-package-below-40",
    "terms-of-use", "privacy-policy",
    "research-education", "research-education/publications", "research-education/news-media",
}


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return "home"
    return path.rstrip("/").split("/")[-1]


def categorize(url: str):
    path = urlparse(url).path
    for prefix, (folder, dtype) in CATEGORY_MAP:
        if prefix in path:
            return folder, dtype
    # page-sitemap fallback
    slug = path.strip("/")
    top = slug.split("/", 1)[0] if slug else ""
    if slug in KEEP_PAGE_SLUGS or top in KEEP_PAGE_SLUGS or not slug:
        return "pages", "page"
    return None  # skip


def yaml_frontmatter(**fields) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            s = str(v).replace('"', '\\"')
            lines.append(f'{k}: "{s}"')
    lines.append("---")
    return "\n".join(lines) + "\n"


def clean_html(html: str) -> tuple[str, str]:
    """Return (title, cleaned_html) — strips nav/footer/scripts/sidebars."""
    soup = BeautifulSoup(html, "lxml")
    title = (soup.title.get_text().strip() if soup.title else "")
    # Meta description as fallback subtitle
    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"].strip()

    for sel in [
        "script", "style", "noscript", "iframe", "svg",
        "nav", "header", "footer", "aside",
        "form",
        ".site-header", ".site-footer", ".menu", ".sidebar",
        ".elementor-location-header", ".elementor-location-footer",
        "#header", "#footer", "#sidebar",
        ".breadcrumb", ".breadcrumbs",
        ".related-posts", ".comments", "#comments",
        ".social-share", ".sharing", ".share-buttons",
        ".cookie", ".popup", ".modal",
        ".search-form", ".search-box",
    ]:
        for tag in soup.select(sel):
            tag.decompose()

    # Prefer specific content containers
    for sel in [
        "article", "main",
        ".entry-content", ".post-content", ".page-content", ".site-main",
        ".elementor-widget-container",  # last-resort container
    ]:
        node = soup.select_one(sel)
        if node and len(node.get_text(strip=True)) > 200:
            return title, str(node), meta_desc
    return title, str(soup.body or soup), meta_desc


def to_markdown(html: str) -> str:
    md = markdownify(html, heading_style="ATX", strip=["a"] if False else None, bullets="-")
    # collapse >2 blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def main():
    urls_by_sitemap = json.loads((DISCOVERY / "urls.json").read_text(encoding="utf-8"))

    # Collect URLs to scrape
    to_scrape = []
    for sm, urls in urls_by_sitemap.items():
        if sm not in INCLUDE_SITEMAPS:
            continue
        for u in urls:
            if u.endswith(".xml"):
                continue
            cat = categorize(u)
            if cat is None:
                continue
            to_scrape.append((u, cat))

    print(f"Scraping {len(to_scrape)} pages...")
    KB.mkdir(exist_ok=True)

    manifest = []

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

        # Warm up Anubis
        print("Warming up on homepage ...")
        page.goto("https://cytecare.com/", wait_until="domcontentloaded", timeout=60000)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if "Checking your browser" not in page.title():
                    break
            except Exception:
                pass
            time.sleep(0.5)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        print(f"  homepage title: {page.title()!r}")

        api = ctx.request

        for i, (url, (folder, dtype)) in enumerate(to_scrape, 1):
            slug = slug_from_url(url)
            out_dir = KB / folder
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{slug}.md"

            if out_path.exists() and out_path.stat().st_size > 500:
                # already scraped, skip
                manifest.append({"url": url, "path": str(out_path.relative_to(ROOT)), "type": dtype, "cached": True})
                if i % 20 == 0:
                    print(f"  [{i}/{len(to_scrape)}] cached: {slug}")
                continue

            try:
                r = api.get(url)
                if r.status != 200:
                    print(f"  [{i}/{len(to_scrape)}] ! {r.status} {url}")
                    continue
                html = r.text()
            except Exception as e:
                print(f"  [{i}/{len(to_scrape)}] ! ERR {url}: {e}")
                continue

            title, content_html, meta_desc = clean_html(html)
            md = to_markdown(content_html)
            fm = yaml_frontmatter(
                title=title,
                source_url=url,
                scraped_at=SCRAPED_AT,
                type=dtype,
                folder=folder,
                slug=slug,
                description=meta_desc,
            )
            out_path.write_text(fm + "\n" + md + "\n", encoding="utf-8")
            manifest.append({"url": url, "path": str(out_path.relative_to(ROOT)), "type": dtype, "cached": False})
            print(f"  [{i}/{len(to_scrape)}] {folder}/{slug}.md  ({len(md)} chars)")
            time.sleep(0.4)  # be polite

        browser.close()

    (KB / "_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nDone. Manifest: {KB / '_manifest.json'}")


if __name__ == "__main__":
    main()
