"""Build kb/INDEX.md — a navigable table of contents over the scraped KB."""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
KB = ROOT / "kb"

FOLDERS = [
    ("doctors",     "Doctors & Specialists",      "One file per doctor. Frontmatter has specialty; body has bio, qualifications, experience."),
    ("specialties", "Specialties & Treatments",   "Oncology, cardiology, neurology, orthopedics, gynaecology, etc. Also cancer-diagnosis services (pathology, radiology, biopsy)."),
    ("services",    "Support Services & Clinics", "Blood centre, psycho-oncology, patient navigators, and 10+ specialty clinics (diabetes, prostate, COPD, etc.)."),
    ("team",        "Leadership & Team",          "Non-clinical leadership: CFO, admin, ops."),
    ("pages",       "Hospital Pages",             "Home, about, appointment info, health packages, contact, policies."),
]


def read_frontmatter(md_path: Path):
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r'^(\w+):\s*"?(.*?)"?$', line)
            if mm:
                fm[mm.group(1)] = mm.group(2)
    body = text[m.end():] if m else text
    return fm, body


def one_liner(body: str, fm: dict) -> str:
    # Prefer meta description
    desc = fm.get("description", "").strip()
    if desc:
        return desc
    # else first meaningful paragraph
    for para in body.split("\n\n"):
        s = re.sub(r"[\[\]()!#*_>`]", "", para).strip()
        s = re.sub(r"\s+", " ", s)
        if len(s) > 60 and not s.startswith(("- ", "http")):
            return s[:180] + ("..." if len(s) > 180 else "")
    return ""


def title_of(fm: dict, slug: str) -> str:
    t = fm.get("title", "")
    # Trim marketing suffix after " - " or " | " for readability
    t = re.split(r"\s+[-|]\s+", t)[0].strip()
    return t or slug


def main():
    lines = [
        "# Cytecare Knowledge Base — Index",
        "",
        "Scraped from https://cytecare.com on 2026-08-20.",
        "",
        "Cytecare is a 150-bed oncology-focused multi-specialty hospital in Yelahanka, Bangalore.",
        "",
        "This KB is organized for a hospital demo agent. Files have YAML frontmatter with `title`, `source_url`, `type`, `slug`, and `description`.",
        "",
        "## Contents",
        "",
    ]
    counts = {}
    for folder, label, _ in FOLDERS:
        n = len(list((KB / folder).glob("*.md")))
        counts[folder] = n
        lines.append(f"- [{label}](#{folder}) — {n} files")
    lines.append("")

    for folder, label, blurb in FOLDERS:
        lines.append(f"## {label}")
        lines.append("")
        lines.append(f"*{blurb}*")
        lines.append("")

        entries = []
        for md in sorted((KB / folder).glob("*.md")):
            fm, body = read_frontmatter(md)
            title = title_of(fm, md.stem)
            summary = one_liner(body, fm)
            rel = md.relative_to(KB).as_posix()
            entries.append((title, rel, summary))

        for title, rel, summary in entries:
            if summary:
                lines.append(f"- [{title}]({rel}) — {summary}")
            else:
                lines.append(f"- [{title}]({rel})")
        lines.append("")

    (KB / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {KB / 'INDEX.md'}")
    for folder, n in counts.items():
        print(f"  {folder}: {n}")


if __name__ == "__main__":
    main()
