#!/usr/bin/env python3
"""
Phase 5 Scraper v4 — Uses sc-courselink and table structure from SmartCatalog.
Two phases: discover URLs, then fetch and parse degree pages.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
import sys
import os

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

BASE = "https://inter.smartcatalogiq.com"
ROOT = "/en/2025-2026/general-catalog-2025-2026/programs-of-study-undergraduate-associate-and-bachelor-s-degree-programs"

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (curricular-sequence-tool)"})

def fetch(url):
    try:
        r = S.get(url, timeout=30)
        return BeautifulSoup(r.text, "html.parser") if r.status_code == 200 else None
    except:
        return None

def discover_urls():
    """Crawl index + landing pages to find all degree URLs."""
    soup = fetch(f"{BASE}{ROOT}")
    if not soup:
        sys.exit("Cannot fetch main index")

    links = {}
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if ROOT + "/" in h:
            path = h.replace(ROOT + "/", "").strip("/")
            if path:
                links[path] = a.get_text(strip=True)

    # Crawl landing pages (top-level, no slash)
    top = [p for p in links if "/" not in p]
    for lp in top:
        sub = fetch(f"{BASE}{ROOT}/{lp}")
        if not sub:
            continue
        for a in sub.find_all("a", href=True):
            h = a["href"]
            if f"{ROOT}/{lp}/" in h:
                path = h.replace(ROOT + "/", "").strip("/")
                if path not in links:
                    links[path] = a.get_text(strip=True)
        time.sleep(0.15)

    return links

def extract(url, target_id):
    """Parse a degree page using SmartCatalog's HTML structure."""
    soup = fetch(url)
    if not soup:
        return None

    text = soup.get_text()

    # Total credits from page text
    total_credits = None
    for pat in [
        r'Total\s+(?:Number\s+of\s+)?Credits?\s*[:\s]*(\d+(?:\s*[-\u2013]\s*\d+)?)',
        r'(\d+(?:\s*[-\u2013]\s*\d+)?)\s+Total\s+Credits?',
    ]:
        m = re.search(pat, text, re.I)
        if m:
            total_credits = m.group(1).strip()
            break

    # Extract ALL course codes via sc-courselink anchors
    all_courses = {}
    for a in soup.find_all("a", class_="sc-courselink"):
        code = a.get_text(strip=True)
        href = a.get("href", "")
        if re.match(r'^[A-Z]{2,4}\s+\d{4}[A-Z]?$', code):
            all_courses[code] = href

    # Extract categories: walk through headings and tables
    categories = []
    current = None

    # Find all headings and tables in order
    body = soup.find("div", id="main") or soup.find("body")
    for elem in body.find_all(["h2", "h3", "h4", "h5", "table"]):
        if elem.name in ("h2", "h3", "h4", "h5"):
            h = elem.get_text(strip=True)
            if not h or len(h) < 3:
                continue
            if any(s in h.lower() for s in ["print", "share", "note:", "admission"]):
                continue
            cr = None
            m = re.search(r'(\d+(?:\s*[-\u2013]\s*\d+)?)\s*(?:credits?|cr)', h, re.I)
            if m:
                cr = m.group(1)
            current = {"label": h, "courses": [], "credits": cr, "rows": []}
            categories.append(current)

        elif elem.name == "table" and current is not None:
            for row in elem.find_all("tr"):
                cells = row.find_all("td")
                if not cells:
                    continue

                # Extract course code from sc-courselink or first cell
                course_link = row.find("a", class_="sc-courselink")
                code = course_link.get_text(strip=True) if course_link else None

                # Get all cell text
                cell_texts = [c.get_text(strip=True) for c in cells]
                row_str = " | ".join(cell_texts)

                if code and re.match(r'^[A-Z]{2,4}\s+\d{4}[A-Z]?$', code):
                    current["courses"].append(code)

                current["rows"].append(row_str)

    # Also extract course codes from non-table text (e.g., "or" options in paragraphs)
    course_re = re.compile(r'\b([A-Z]{2,4})\s+(\d{4}[A-Z]?)\b')
    skip = {"HTTP","HTML","ISBN","ISSN","ABET","STEM","LEAD","CASP","PLUS","FALL","YEAR"}
    text_courses = set()
    for m in course_re.finditer(text):
        d, n = m.groups()
        if d not in skip:
            text_courses.add(f"{d} {n}")

    return {
        "target_id": target_id,
        "url": url,
        "total_credits": total_credits,
        "all_courses": sorted(all_courses.keys()),
        "all_courses_with_links": all_courses,
        "text_courses": sorted(text_courses),
        "categories": [c for c in categories if c["courses"] or c["rows"]],
    }

# Target degrees
TARGETS = [
    ("nursing-bsn", ["nursing.bsn/nursing.bsn", "bachelor.*nursing.*bsn"], "changed"),
    ("social-sciences-ba", ["social.sciences.ba/social.sciences", "social.sciences.ba$"], "changed"),
    ("biomedical-sciences-bs", ["biomedical.sciences.bs/biomed", "biomedical.sciences.bs$"], "changed"),
    ("social-work-ba", ["social.work.ba/social.work"], "changed"),
    ("biology-bs", ["biology.bs/biology.bs"], "changed"),
    ("marine-sciences-bs", ["marine.sciences.bs/marine.sciences.bs"], "changed"),
    ("natural-sciences-bs", ["natural.sciences.bs/natural.sciences", "natural.sciences.bs$"], "changed"),
    ("toxicology-bs", ["toxicology.bs/toxicology.bs"], "changed"),
    ("computer-science-aas", ["computer.science.*(aas|associate)", "computer-science-aas"], "changed"),
    ("agronomy-bas", ["agronomy.bas/agronomy", "agronomy-bas$"], "changed"),
    ("animal-science-pre-vet-bs", ["animal.science.*vet.*bs/", "animal.science.*pre.*vet"], "changed"),
    ("fine-arts-bfa", ["fine.arts.bfa/fine.arts"], "changed"),
    ("early-childhood-education-k5-ba", ["early.*childhood.*k.?5", "early.*childhood.*k-5"], "changed"),
    ("agricultural-precision-aas", ["agricultural.precision.*aas/", "agricultural-precision-aas$"], "new"),
    ("cyber-security-bs", ["science.in.cyber.security/science", "cyber.security.*bs/"], "new"),
    ("electrical-engineering-technology-as", ["electrical.engineering.technology.as/elec", "electrical-engineering-technology-as$"], "new"),
    ("engineering-technology-renewable-energy-as", ["engineering.technology.*renewable.*energy/eng", "engineering-technology-in-renewable-energy$"], "new"),
    ("geomatics-civil-engineering-technology-as", ["geomatics.*civil.*engineering.*technology/geo", "geomatics.*civil.*engineering.*technology-as$"], "new"),
    ("healthcare-billing-aa", ["healthcare.billing.*aa/", "healthcare-billing-aa$"], "new"),
    ("integral-beauty-aa", ["integral.beauty.*aa/", "integral-beauty-aa$"], "new"),
    ("molecular-medicine-bioprocesses-bs", ["molecular.medicine.*bioprocesses.*bs/", "molecular-medicine-and-bioprocesses-bs$"], "new"),
    ("nursing-rn-to-bsn", ["nursing.*rn.*bsn/", "nursing-rn-to-bsn"], "new"),
    ("renewable-energy-pv-aa", ["renewable.energy.*photovoltaic/", "renewable-energy-technology-with-photovoltaic"], "new"),
    ("sports-technology-ba", ["sports.technology.ba/sports.technology.ba"], "new"),
    ("diagnostic-ultrasound-aas", ["diagnostic.ultrasound/diagnostic.ultrasound", "diagnostic-ultrasound$"], "new"),
    ("veterinary-technician-aas", ["veterinary.technician.*aas/", "veterinary-technician-aas$"], "new"),
    ("veterinary-technology-bs", ["veterinary.technology.*bs/", "veterinary-technology-bs$"], "new"),
    ("visual-arts-art-teaching-ba", ["artes.visuales.*ba/", "artes-visuales-ba$"], "new"),
    ("early-childhood-education-pk4-ba", ["early.*childhood.*pk.?4", "preschool.*fourth.*pk"], "new"),
    ("physical-education-k12-ba", ["physical.education.*k.?12.ba", "physical-education-k-12"], "new"),
]

def match(target_id, keywords, links):
    """Match a target to discovered URLs, preferring nested (deeper) pages."""
    candidates = []
    for path, name in links.items():
        for kw in keywords:
            if re.search(kw, path, re.I):
                depth = path.count("/")
                candidates.append((depth, path, name))
                break
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]

def main():
    print("Discovering URLs...", file=sys.stderr)
    links = discover_urls()
    print(f"Found {len(links)} URLs", file=sys.stderr)

    # Dump full URL index for debugging
    with open("data/extraction-notes/url-index.json", "w", encoding="utf-8") as f:
        json.dump(dict(sorted(links.items())), f, indent=2, ensure_ascii=False)

    results = {}
    failed = []

    for tid, kws, dtype in TARGETS:
        path = match(tid, kws, links)
        if not path:
            failed.append({"id": tid, "reason": "no URL match"})
            print(f"  {tid}: NO MATCH", file=sys.stderr)
            continue

        url = f"{BASE}{ROOT}/{path}"
        print(f"  {tid} -> {path}", file=sys.stderr)
        data = extract(url, tid)
        if data:
            data["type"] = dtype
            data["matched_path"] = path
            nc = len(data["all_courses"])
            nt = len(data["text_courses"])
            cr = data["total_credits"] or "?"
            print(f"    {nc} linked courses, {nt} text courses, {cr} credits", file=sys.stderr)

            if nc < 5:
                print(f"    WARNING: few linked courses — may be landing page", file=sys.stderr)
            results[tid] = data
        else:
            failed.append({"id": tid, "reason": "fetch failed", "url": url})
            print(f"    FAILED", file=sys.stderr)

        time.sleep(0.3)

    output = {"results": results, "failed": failed}
    print(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n=== {len(results)}/{len(TARGETS)} OK, {len(failed)} failed ===", file=sys.stderr)

if __name__ == "__main__":
    main()
