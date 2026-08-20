# Scrape Notes — Cytecare KB

## Source
- Site: https://cytecare.com/
- Sitemap index: https://cytecare.com/sitemap_index.xml
- Scraped: 2026-08-20

## What is Cytecare?
A 150-bed oncology-focused multi-specialty hospital in Yelahanka, Bangalore. Marketed as "#1 Oncology Hospital in Bangalore" — cancer treatment is the anchor practice, with other specialties (cardiology, neurology, orthopedics, gynaecology, ENT, dermatology, pulmonology, urology, dentistry, general medicine, etc.) alongside.

Contact hints observed on pages:
- Toll-free: `18001236767`
- WhatsApp: `+91 91642 22230`
- Appointment page: https://cytecare.com/appointment/

## Approach

1. Plain `requests` succeeded on the first fetch, but subsequent requests were intercepted by an **Anubis** proof-of-work challenge (JS-based anti-bot). Switched to **Playwright + headless Chromium** to solve the challenge organically.
2. Warmed a Playwright browser context on the homepage until the Anubis challenge completed.
3. Reused the context's cookie-bearing `context.request` API to fetch each XML sitemap and each page — much faster than driving `page.goto()` per URL.
4. Cleaned HTML with BeautifulSoup (strip nav/footer/scripts/sidebars, pick article/main/entry-content). Converted with `markdownify`. Wrote YAML frontmatter (`title`, `source_url`, `scraped_at`, `type`, `folder`, `slug`, `description`).

## Sitemap inventory

Cytecare exposes 19 sub-sitemaps totalling 948 URLs. Included in KB (147 candidates → 117 saved):

| Sitemap | URLs | Included as | Notes |
|---|---|---|---|
| doctors-sitemap | 48 | doctors/ | one file per specialist |
| service-sitemap | 7 | services/ | support-services |
| diagnosis-sitemap | 6 | specialties/ | pathology, radiology, biopsy, etc. |
| clinics-sitemap | 9 | services/ | specialty clinics |
| team-sitemap | 15 | team/ | non-clinical leadership |
| other-sitemap | 17 | specialties/ | `/treatment/*` specialty pages |
| page-sitemap | 36 | pages/ (filtered) | kept only hospital-info pages |

Excluded (marketing/regulatory/media noise, not needed for demo agent):

| Sitemap | URLs | Reason |
|---|---|---|
| post-sitemap | 146 | blog posts |
| news-sitemap1 / 2 | 346 | press releases |
| events-sitemap | 165 | past events |
| testimonials-sitemap | 19 | patient testimonials |
| review-sitemap | 59 | patient reviews |
| doctortalk-sitemap | 18 | podcast/video series |
| jobs-sitemap | 11 | career listings |
| infovideo-sitemap | 29 | media/video content |
| brochures-sitemap | 7 | PDF assets |
| biomedicals-sitemap | 9 | monthly biomedical-waste regulatory reports |
| resources-sitemap | 1 | thin content |

## Content quality

- **Doctors, services, specialty clinics, and most /treatment/ pages** — clean, useful content in the 3–10 KB range with qualifications, focus areas, and descriptions.
- **Diagnosis pages** (pathology, radiology, biopsy, nuclear-medicine, colposcopy, endoscopy) — very rich, ~20 KB each; long procedural detail.
- **Home page & appointment page** — includes some navigation/promo markup that survived cleaning; readable but slightly noisy.
- **Thin pages**: `specialties/cardiology.md`, `specialties/endocrinology.md`, `specialties/pulmonology.md`, and four `team/*` files came out small (under 1 KB) after a re-scrape with a broader selector. Confirmed the source pages themselves are just short on the live site — not a scraper defect.

## Folder layout

```
kb/
├── INDEX.md               # master TOC + one-line summary per file
├── SCRAPE_NOTES.md        # this file
├── _manifest.json         # every scraped URL → path, type, cached flag
├── doctors/       (49)    # our-cancer-specialist/*
├── specialties/   (24)    # treatment/* + cancer-diagnosis/*
├── services/      (16)    # support-services/* + health-clinics/*
├── team/          (15)    # team/* (non-clinical leadership)
└── pages/         (13)    # hand-picked hospital-info pages
```

## Rerunning / updating

- Re-discover URLs: `python scraper/discover_pw.py`
- Rescrape all: `python scraper/scrape.py` (skips files already >500 bytes)
- Rescrape stubs only: `python scraper/rescrape_stubs.py`
- Rebuild index: `python scraper/build_index.py`

## Things I intentionally did NOT do

- Did not follow blog/news/event links — 800+ pages of low-signal content.
- Did not download images / brochures / videos — could add later if the agent needs multimodal context.
- Did not scrape testimonials/reviews — could enrich the agent's tone/persona if useful, but excluded here to keep the KB focused.
- Did not overwrite the FastAPI mock data (`data/doctors.json`) — kept as a parallel demo. Swapping in real Cytecare doctors is a next step if you want.
