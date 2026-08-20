"""Quick probe: can we reach cytecare.com with plain requests?"""
import sys
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

for url in [
    "https://cytecare.com/robots.txt",
    "https://cytecare.com/sitemap.xml",
    "https://cytecare.com/",
]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        print(f"{url} -> {r.status_code} ({len(r.content)} bytes) final={r.url}")
        print("  server:", r.headers.get("server"))
        print("  ctype :", r.headers.get("content-type"))
        snippet = r.text[:400].replace("\n", " ")
        print("  head  :", snippet)
        print()
    except Exception as e:
        print(f"{url} -> ERROR {type(e).__name__}: {e}")
        print()
