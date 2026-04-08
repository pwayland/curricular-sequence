#!/usr/bin/env python3
"""Fix up the 3 missing degrees by fetching them directly and merging into results."""

import requests
from bs4 import BeautifulSoup
import json
import re
import sys
import os

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

BASE = "https://inter.smartcatalogiq.com"
ROOT = "/en/2025-2026/general-catalog-2025-2026/programs-of-study-undergraduate-associate-and-bachelor-s-degree-programs"

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0"})

FIXES = {
    "early-childhood-education-k5-ba": f"{ROOT}/early-childhood-education/early-childhood-education-elementary-primary-level-k-3-ba",
    "cyber-security-bs": f"{ROOT}/science-in-cyber-security",
    "physical-education-k12-ba": f"{ROOT}/physical-education-and-health-education/physical-education-and-health-education-requirements",
}

def extract(url, tid):
    r = S.get(f"{BASE}{url}", timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text()

    total_credits = None
    for pat in [
        r'Total\s+(?:Number\s+of\s+)?Credits?\s*[:\s]*(\d+(?:\s*[-\u2013]\s*\d+)?)',
        r'(\d+(?:\s*[-\u2013]\s*\d+)?)\s+Total\s+Credits?',
    ]:
        m = re.search(pat, text, re.I)
        if m:
            total_credits = m.group(1).strip()
            break

    all_courses = {}
    for a in soup.find_all("a", class_="sc-courselink"):
        code = a.get_text(strip=True)
        href = a.get("href", "")
        if re.match(r'^[A-Z]{2,4}\s+\d{4}[A-Z]?$', code):
            all_courses[code] = href

    categories = []
    current = None
    body = soup.find("div", id="main") or soup.find("body")
    for elem in body.find_all(["h2", "h3", "h4", "h5", "table"]):
        if elem.name in ("h2", "h3", "h4", "h5"):
            h = elem.get_text(strip=True)
            if not h or len(h) < 3 or any(s in h.lower() for s in ["print", "share", "note:", "admission"]):
                continue
            cr = None
            m = re.search(r'(\d+(?:\s*[-\u2013]\s*\d+)?)\s*(?:credits?|cr)', h, re.I)
            if m: cr = m.group(1)
            current = {"label": h, "courses": [], "credits": cr, "rows": []}
            categories.append(current)
        elif elem.name == "table" and current is not None:
            for row in elem.find_all("tr"):
                cells = row.find_all("td")
                if not cells: continue
                cl = row.find("a", class_="sc-courselink")
                code = cl.get_text(strip=True) if cl else None
                cell_texts = [c.get_text(strip=True) for c in cells]
                row_str = " | ".join(cell_texts)
                if code and re.match(r'^[A-Z]{2,4}\s+\d{4}[A-Z]?$', code):
                    current["courses"].append(code)
                current["rows"].append(row_str)

    return {
        "target_id": tid,
        "url": f"{BASE}{url}",
        "matched_path": url.replace(ROOT + "/", ""),
        "total_credits": total_credits,
        "all_courses": sorted(all_courses.keys()),
        "all_courses_with_links": all_courses,
        "text_courses": [],
        "categories": [c for c in categories if c["courses"] or c["rows"]],
    }

# Load existing results
with open("data/extraction-notes/phase5-scraped.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for tid, path in FIXES.items():
    print(f"Fetching {tid}...", file=sys.stderr)
    result = extract(path, tid)
    result["type"] = "changed" if tid in ("early-childhood-education-k5-ba",) else "new"
    if tid == "cyber-security-bs":
        result["type"] = "new"
    if tid == "physical-education-k12-ba":
        result["type"] = "new"
    n = len(result["all_courses"])
    cr = result["total_credits"] or "?"
    print(f"  {n} courses, {cr} credits", file=sys.stderr)
    data["results"][tid] = result

# Remove from failed
data["failed"] = [f for f in data["failed"] if f["id"] not in FIXES]

print(json.dumps(data, indent=2, ensure_ascii=False))
