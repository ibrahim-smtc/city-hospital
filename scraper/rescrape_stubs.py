"""Rescrape pages that came out as tiny stubs, using a smarter content selector."""
import json
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
KB = ROOT / "kb"
SCRAPED_AT = "2026-08-20"


def yaml_frontmatter(**fields) -> str:
    lines = ["---"]
    for k, v in fields.items():
        s = str(v).replace('"', '\\"')
        lines.append(f'{k}: "{s}"')
    lines.append("---")
    return "\n".join(lines) + "\n"


def clean_html_greedy(html: str):
    """Return (title, content_html, meta_desc). Pick the container with the MOST visible text."""
    soup = BeautifulSoup(html, "lxml")
    title = (soup.title.get_text().strip() if soup.title else "")
    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"].strip()

    # Strip noise first
    for sel in [
        "script", "style", "noscript", "iframe", "svg",
        "nav", "header", "footer", "aside", "form",
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

    candidates = []
    for sel in [
        "article", "main",
        ".entry-content", ".post-content", ".page-content", ".site-main",
        ".elementor", ".elementor-section-wrap", ".content-area",
    ]:
        for node in soup.select(sel):
            txt = node.get_text(strip=True)
            if len(txt) > 300:
                candidates.append((len(txt), node))

    if candidates:
        candidates.sort(key=lambda x: -x[0])
        return title, str(candidates[0][1]), meta_desc

    body = soup.body or soup
    return title, str(body), meta_desc


def to_markdown(html: str) -> str:
    md = markdownify(html, heading_style="ATX", bullets="-")
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


# The 8 stubs and their source URLs (from manifest)
STUBS = {
    "specialties/cardiology.md":            "https://cytecare.com/treatment/cardiology/",
    "specialties/endocrinology.md":         "https://cytecare.com/treatment/endocrinology/",
    "specialties/nephrology-treatment.md":  "https://cytecare.com/treatment/nephrology-treatment/",
    "specialties/pulmonology.md":           "https://cytecare.com/treatment/pulmonology/",
    "team/jayappa-m.md":                    "https://cytecare.com/team/jayappa-m/",
    "team/raj-sarvottam.md":                "https://cytecare.com/team/raj-sarvottam/",
    "team/rekha-shivakumar.md":             "https://cytecare.com/team/rekha-shivakumar/",
    "team/sowmya-kp.md":                    "https://cytecare.com/team/sowmya-kp/",
}


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

        print("Warming up ...")
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

        api = ctx.request
        for rel_path, url in STUBS.items():
            out = KB / rel_path
            folder = rel_path.split("/")[0]
            slug = rel_path.split("/")[-1].replace(".md", "")
            print(f"  rescrape {rel_path} <- {url}")
            r = api.get(url)
            if r.status != 200:
                print(f"    ! {r.status}")
                continue
            html = r.text()
            title, content_html, meta_desc = clean_html_greedy(html)
            md = to_markdown(content_html)
            fm = yaml_frontmatter(
                title=title,
                source_url=url,
                scraped_at=SCRAPED_AT,
                type="specialty" if folder == "specialties" else "team_member",
                folder=folder,
                slug=slug,
                description=meta_desc,
            )
            out.write_text(fm + "\n" + md + "\n", encoding="utf-8")
            print(f"    -> {len(md)} chars")
            time.sleep(0.4)

        browser.close()


if __name__ == "__main__":
    main()
