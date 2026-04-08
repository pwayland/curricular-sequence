#!/usr/bin/env python3
"""
Batch scrape 142 truly new courses from SmartCatalog.
Extracts title, credits, prerequisites from each course page.
Appends to courses-2025-26.yaml.
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

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (curricular-sequence-tool)"})

# Load the course links from generation output
with open("data/extraction-notes/phase5-generation.json", "r", encoding="utf-8") as f:
    gen = json.load(f)

# Load existing 2020-21 and 2025-26 courses
import yaml
with open("data/courses/courses-2020-21.yaml", "r", encoding="utf-8") as f:
    c20 = yaml.safe_load(f)
with open("data/courses/courses-2025-26.yaml", "r", encoding="utf-8") as f:
    c25 = yaml.safe_load(f)

existing = set(c20.get("courses", {}).keys()) | set(c25.get("courses", {}).keys())

# Courses to scrape
new_courses = sorted(c for c in gen["new_courses"] if c not in existing)
course_links = gen.get("new_course_links", {})

print(f"Scraping {len(new_courses)} new courses...", file=sys.stderr)

def scrape_course(code, link):
    """Fetch a course page and extract title, credits, prereqs."""
    url = f"{BASE}{link}"
    try:
        r = S.get(url, timeout=30)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
    except:
        return None

    text = soup.get_text()

    # Title: usually in h1 or first heading
    title = None
    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text(strip=True)
        # Format: "DEPT NNNN - Course Title" or "Course Title"
        m = re.match(r'[A-Z]{2,4}\s+\d{4}[A-Z]?\s*[-–—]\s*(.+)', h1_text)
        if m:
            title = m.group(1).strip()
        else:
            title = h1_text

    # Credits
    credits = None
    cr_patterns = [
        r'(\d+)\s+(?:Credit|credit)s?\b',
        r'Credits?:\s*(\d+)',
        r'(\d+)\s+cr\.?\b',
    ]
    for pat in cr_patterns:
        m = re.search(pat, text)
        if m:
            credits = int(m.group(1))
            break

    # Prerequisites
    prereqs = []
    prereq_re = re.compile(r'[Pp]rerequisites?\s*:?\s*(.+?)(?:\.|$)', re.MULTILINE)
    m = prereq_re.search(text)
    if m:
        prereq_text = m.group(1)
        # Extract course codes from prereq text
        course_re = re.compile(r'([A-Z]{2,4})\s+(\d{4}[A-Z]?)')
        for cm in course_re.finditer(prereq_text):
            dept, num = cm.groups()
            prereqs.append(f"{dept} {num}")

    return {
        "title": title or code,
        "credits": credits or 3,
        "prereqs": prereqs,
    }

results = {}
failed = []

for i, code in enumerate(new_courses):
    # Fix codes with extra spaces
    clean_code = re.sub(r'\s+', ' ', code.strip())

    link = course_links.get(code) or course_links.get(clean_code)
    if not link:
        failed.append(code)
        print(f"  [{i+1}/{len(new_courses)}] {code}: no link", file=sys.stderr)
        continue

    info = scrape_course(code, link)
    if info:
        results[clean_code] = info
        print(f"  [{i+1}/{len(new_courses)}] {clean_code}: {info['title'][:40]} ({info['credits']}cr) prereqs={info['prereqs']}", file=sys.stderr)
    else:
        failed.append(code)
        print(f"  [{i+1}/{len(new_courses)}] {code}: FAILED", file=sys.stderr)

    time.sleep(0.2)

# Generate YAML to append
lines = ["\n  # === New courses scraped from SmartCatalog (Phase 5) ==="]
by_dept = {}
for code, info in results.items():
    dept = code.split()[0]
    if dept not in by_dept:
        by_dept[dept] = []
    by_dept[dept].append((code, info))

for dept in sorted(by_dept.keys()):
    lines.append(f"\n  # {dept}")
    for code, info in sorted(by_dept[dept]):
        title = info["title"].replace('"', '\\"')
        credits = info["credits"]
        prereqs = info["prereqs"]
        lines.append(f"  {code}:")
        lines.append(f'    title: "{title}"')
        lines.append(f"    credits: {credits}")
        if prereqs:
            prereq_str = ", ".join(f'"{p}"' for p in prereqs)
            lines.append(f"    prereqs: [{prereq_str}]")
        else:
            lines.append(f"    prereqs: []")

yaml_block = "\n".join(lines) + "\n"

with open("data/courses/courses-2025-26.yaml", "a", encoding="utf-8") as f:
    f.write(yaml_block)

print(f"\n=== Scraped {len(results)}/{len(new_courses)} courses, {len(failed)} failed ===", file=sys.stderr)
if failed:
    print(f"Failed: {failed}", file=sys.stderr)

# Output summary as JSON
print(json.dumps({
    "scraped": len(results),
    "failed": failed,
    "courses": {k: v for k, v in sorted(results.items())},
}, indent=2, ensure_ascii=False))
