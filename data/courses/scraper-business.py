#!/usr/bin/env python3
"""
Business-school course scraper — fetches courses from SmartCatalog 2021-2022
for 18 department prefixes and appends YAML stubs to courses-2020-21.yaml.
Uses threading (6 workers) for individual course pages.

SmartCatalog structure:
  /courses/{dept-slug}           -> lists sub-levels (1000, 2000, ...)
  /courses/{dept-slug}/{level}   -> lists individual courses
  /courses/{dept-slug}/{level}/{code} -> individual course page
"""

import requests
from bs4 import BeautifulSoup
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

BASE = "https://inter.smartcatalogiq.com"
CATALOG = "/en/2021-2022/catalogo-general-2021-2022/courses"

# 18 target prefixes with known slugs (from catalog index)
DEPT_SLUGS = {
    "MKTG": "mktg-mercadeo",
    "OMSY": "omsy-administraci-n-de-sistemas-de-oficina",
    "MAEC": "maec-econom-a-gerencial",
    "FINA": "fina-finanzas",
    "ITEC": "itec-tecnolog-a-de-la-informaci-n",
    "INTB": "intb-negocios-internacionales",
    "ENTR": "entr-desarrollo-empresarial-y-gerencial",
    "HRMA": "hrma-gerencia-de-recursos-humanos",
    "REAL": "real-bienes-ra-ces",
    "MDME": "mdme-mercadeo-para-mercados-digitales",
    "HCAD": "hcad-administraci-n-de-servicios-de-salud",
    "MGOI": "mgoi-gerencia-e-innovaci-n-organizacional",
    "ORBE": "orbe-organizaci-n-y-banca-electr-nica",
    "OPMS": "opms-gerencia-de-operaciones-de-manufactura-y-servicio",
    "STAT": "stat-estad-stica",
    "SRIM": "srim-administraci-n-de-instalaciones-recreativas-y-deportivas",
    "FSMT": "fsmt-adminsitracion-de-servicios-de-restaurant-y-alimentos",
    "ENDE": "ende-desarrollo-empresarial",
}

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (curricular-sequence-tool)"})

def fetch_soup(url):
    try:
        r = S.get(url, timeout=30)
        return BeautifulSoup(r.text, "html.parser") if r.status_code == 200 else None
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
        return None


def discover_courses_in_dept(prefix, slug):
    """Crawl dept page and sub-level pages to get all course URLs."""
    dept_url = f"{BASE}{CATALOG}/{slug}"
    soup = fetch_soup(dept_url)
    if not soup:
        print(f"  {prefix}: cannot fetch dept page", file=sys.stderr)
        return []

    courses = []
    seen = set()

    def extract_courses(s):
        for a in s.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            if re.match(rf'^{prefix}\s+\d{{4}}[A-Z]?$', text) and text not in seen:
                seen.add(text)
                courses.append((text, href))

    # Extract from main dept page
    extract_courses(soup)

    # Find sub-level pages (1000, 2000, 3000, 4000, etc.)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if re.match(r'^\d{4}$', text) and f"{CATALOG}/{slug}/" in href:
            sub_soup = fetch_soup(f"{BASE}{href}" if not href.startswith("http") else href)
            if sub_soup:
                extract_courses(sub_soup)
            time.sleep(0.1)

    return courses


def fetch_course(code, url):
    """Fetch individual course page and extract title, credits, prereqs."""
    full_url = url if url.startswith("http") else f"{BASE}{url}"
    soup = fetch_soup(full_url)
    if not soup:
        return None

    text = soup.get_text()

    # Title: from h1 which is usually "CODE - Title"
    title = None
    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text(strip=True)
        # Remove the course code prefix
        for sep in [" - ", " – ", " — "]:
            if sep in h1_text:
                title = h1_text.split(sep, 1)[1].strip()
                break
        if not title:
            # h1 might just be the title without code
            cleaned = re.sub(rf'^{re.escape(code)}\s*', '', h1_text).strip()
            if cleaned and cleaned != h1_text:
                title = cleaned

    # Credits
    credits = None
    for pat in [
        r'Credits?\s*[:\s]*(\d+)',
        r'(\d+)\s+Credits?',
        r'Créditos?\s*[:\s]*(\d+)',
        r'(\d+)\s+Créditos?',
    ]:
        m = re.search(pat, text, re.I)
        if m:
            credits = int(m.group(1))
            break

    # Prerequisites from sc-courselink anchors and text
    prereqs = []
    skip_prefixes = {"HTTP","HTML","ISBN","ISSN","ABET","STEM","LEAD","CASP","PLUS","FALL","YEAR"}

    # Search the whole page for prerequisite mentions
    for elem in soup.find_all(["p", "div", "span", "td", "li", "dd"]):
        elem_text = elem.get_text(strip=True).lower()
        if any(kw in elem_text for kw in ["prerequisit", "pre-requisit", "prerrequisit", "pre requisit"]):
            for a in elem.find_all("a", class_="sc-courselink"):
                c = a.get_text(strip=True)
                if re.match(r'^[A-Z]{2,4}\s+\d{4}[A-Z]?$', c) and c != code and c not in prereqs:
                    prereqs.append(c)
            for m in re.finditer(r'\b([A-Z]{2,4})\s+(\d{4}[A-Z]?)\b', elem.get_text()):
                c = f"{m.group(1)} {m.group(2)}"
                if m.group(1) not in skip_prefixes and c != code and c not in prereqs:
                    prereqs.append(c)

    if not title:
        title = code
    if credits is None:
        credits = 3

    return {
        "code": code,
        "title": title,
        "credits": credits,
        "prereqs": sorted(set(prereqs)),
    }


def main():
    print("=== Business School Course Scraper ===", file=sys.stderr)

    # Step 1: Verify slugs by trying to fetch dept pages
    valid_depts = {}
    for pfx, slug in DEPT_SLUGS.items():
        url = f"{BASE}{CATALOG}/{slug}"
        try:
            r = S.head(url, timeout=10)
            if r.status_code == 200:
                valid_depts[pfx] = slug
                print(f"  OK  {pfx} -> {slug}", file=sys.stderr)
            else:
                print(f"  {r.status_code} {pfx} -> {slug}", file=sys.stderr)
        except:
            print(f"  ERR {pfx} -> {slug}", file=sys.stderr)

    print(f"\nValid departments: {len(valid_depts)}/{len(DEPT_SLUGS)}", file=sys.stderr)

    # Step 2: Discover all course URLs per department
    all_course_urls = []
    for pfx in sorted(valid_depts.keys()):
        courses = discover_courses_in_dept(pfx, valid_depts[pfx])
        print(f"  {pfx}: {len(courses)} courses", file=sys.stderr)
        all_course_urls.extend(courses)
        time.sleep(0.15)

    print(f"\nTotal courses to fetch: {len(all_course_urls)}", file=sys.stderr)

    # Step 3: Fetch individual course pages with threading
    results = {}
    errors = []

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(fetch_course, code, url): code
            for code, url in all_course_urls
        }
        done = 0
        for future in as_completed(futures):
            code = futures[future]
            done += 1
            try:
                data = future.result()
                if data:
                    results[data["code"]] = data
                else:
                    errors.append(code)
            except Exception as e:
                errors.append(code)
                print(f"  ERROR {code}: {e}", file=sys.stderr)

            if done % 25 == 0:
                print(f"  Fetched {done}/{len(all_course_urls)}", file=sys.stderr)

    print(f"\nFetched {len(results)} courses, {len(errors)} errors", file=sys.stderr)
    if errors:
        print(f"Errors: {errors}", file=sys.stderr)

    # Step 4: Output YAML
    by_prefix = {}
    for code, data in sorted(results.items()):
        pfx = code.split()[0]
        by_prefix.setdefault(pfx, []).append(data)

    yaml_lines = []
    for pfx in sorted(by_prefix.keys()):
        yaml_lines.append(f"  # ── {pfx} {'─' * (52 - len(pfx))}")
        for c in sorted(by_prefix[pfx], key=lambda x: x["code"]):
            yaml_lines.append(f"  {c['code']}:")
            title = c["title"].replace('"', '\\"')
            yaml_lines.append(f'    title: "{title}"')
            yaml_lines.append(f"    credits: {c['credits']}")
            if c["prereqs"]:
                prereq_str = ", ".join(f'"{p}"' for p in c["prereqs"])
                yaml_lines.append(f"    prereqs: [{prereq_str}]")
            else:
                yaml_lines.append(f"    prereqs: []")

    print("\n".join(yaml_lines))

    # Summary
    print(f"\n=== Done: {len(results)} courses in {len(by_prefix)} departments ===", file=sys.stderr)
    for pfx in sorted(by_prefix.keys()):
        print(f"  {pfx}: {len(by_prefix[pfx])}", file=sys.stderr)


if __name__ == "__main__":
    main()
