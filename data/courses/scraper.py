"""
Scraper for Inter American University 2021-2022 SmartCatalog
Fetches all course details (title, credits, prereqs) for 83 departments.
Writes data/courses/courses-2020-21.yaml
"""

import urllib.request
import urllib.error
import re
import time
import html as html_module
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

BASE = "https://inter.smartcatalogiq.com"
CATALOG = "/en/2021-2022/catalogo-general-2021-2022/courses"

# All 83 dept slugs that have new courses needed
DEPT_SLUGS = {
    "ACCT": "acct-contabilidad",
    "ADEV": "adev-desarrollo-de-aplicaciones",
    "AGRO": "agro-agronom-a",
    "ANTH": "anth-antropolog-a",
    "ARED": "ared-ense-anza-del-arte",
    "AREN": "aren-ingenier-a-arquitect-nica",
    "ARTS": "arts-artes-pl-sticas",
    "AWSC": "awsc-ciencias-de-aviaci-n",
    "BADM": "badm-administraci-n-de-empresas",
    "BIIN": "biin-bioinform-tica",
    "BIOL": "biol-biolog-a",
    "BIOT": "biot-biotecnolog-a",
    "BIPS": "bips-biopsicolog-a",
    "BMSC": "bmsc-ciencias-biom-dicas",
    "CARD": "card-cuidado-cardiorrespiratorio",
    "CHAP": "chap-capellan-a-institucional",
    "CHEM": "chem-qu-mica",
    "CJUS": "cjus-justicia-criminal-e-investigaci-n-criminal",
    "COEN": "coen-ingenier-a-de-computadoras",
    "COMF": "comf-ciencias-forenses-inform-tica-forense-y-biolog-a-forense",
    "COMP": "comp-ciencias-de-computadoras",
    "COMU": "comu-comunicaciones-fotograf-a-y-comunicaci-n-en-producci-n-para-medios",
    "COTN": "cotn-tecnolog-a-de-computadoras-y-redes",
    "CRIM": "crim-criminolog-a",
    "CTMR": "ctmr-tomograf-a-computadorizada-y-resonancia-magn-tica",
    "CYBE": "cybe-delitos-cibern-ticos",
    "DGDM": "dgdm-dise-o-gr-fico-y-multimedios",
    "DSGN": "dsgn-dise-o",
    "EDUC": "educ-educaci-n",
    "ELEC": "elec-tecnolog-a-de-ingenier-a-electr-nica",
    "ELEN": "elen-ingenier-a-el-ctrica",
    "ENGL": "engl-ingl-s",
    "ENGR": "engr-ingenier-a-general",
    "EVSC": "evsc-ciencias-ambientales",
    "EVTH": "evth-tecnolog-a-ambiental",
    "FORS": "fors-ciencias-forenses-inform-tica-forense-y-biolog-a-forense",
    "FREN": "fren-franc-s",
    "FSMT": "fsmt-adminsitracion-de-servicios-de-restaurant-y-alimentos",
    "GAME": "game-dise-o-y-desarrollo-de-videojuegos",
    "GASC": "gasc-artes-culinarias-y-ciencias-de-la-gastronom-a",
    "GEOG": "geog-geograf-a",
    "GERM": "germ-alem-n",
    "GERO": "gero-gerontolog-a",
    "HESC": "hesc-ciencias-de-la-salud",
    "HIST": "hist-historia",
    "HMGT": "hrmt-gerencia-de-hoteles-y-restaurantes",
    "HPER": "hper-salud-educaci-n-f-sica-y-recreaci-n",
    "HUMA": "huma-lenguas-modernas",
    "INEN": "inen-ingenier-a-industrial",
    "ITAL": "ital-italiano",
    "MASC": "masc-ciencias-marinas",
    "MATH": "math-matem-ticas",
    "MECN": "mecn-ingenier-a-mec-nica",
    "MEDT": "medt-tecnolog-a-m-dica",
    "MEEM": "meem-emergencias-m-dicas",
    "MICR": "micr-microbiolog-a",
    "MUED": "mued-ense-anza-de-m-sica",
    "MUSI": "musi-m-sica",
    "NANO": "nano-nanotecnolog-a",
    "NTEL": "ntel-redes-y-telecomunicaciones",
    "NURS": "nurs-enfermer-a",
    "OCTH": "octh-terapia-ocupacional",
    "OPST": "opst-tecnolog-a-en-ciencias-pticas",
    "PHAR": "phar-t-cnico-de-farmacia",
    "PHIL": "phil-filosof-a",
    "PHTH": "phth-asistente-del-terapista-f-sico",
    "PHYS": "phys-f-sica",
    "POLS": "pols-ciencias-pol-ticas",
    "PORT": "port-portugu-s",
    "PSYC": "psyc-psicolog-a",
    "RATE": "rate-tecnolog-a-radiol-gica",
    "RELI": "reli-religi-n",
    "SECU": "secu-seguridad",
    "SOCI": "soci-sociolog-a",
    "SONO": "sono-sonograf-a-m-dica",
    "SOWO": "sowo-trabajo-social",
    "SPAN": "span-espa-ol",
    "SPTH": "spth-terapia-del-habla-y-lenguaje",
    "THEA": "thea-teatro",
    "TOXI": "toxi-toxicolog-a",
    "TURI": "turi-turismo",
    "VETC": "vetc-veterinaria",
    "VGMA": "vgma-videojuegos-y-aplicaciones-m-viles",
}

print_lock = Lock()

def fetch(url, retries=2):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt < retries:
                time.sleep(1)
        except Exception:
            if attempt < retries:
                time.sleep(1)
    return None

def get_course_urls_for_dept(prefix, slug):
    """Fetch dept listing and return list of (course_code, url) pairs."""
    url = f"{BASE}{CATALOG}/{slug}"
    html = fetch(url)
    if not html:
        return []
    # Find all links to individual course pages under this slug
    pattern = rf'href="(/en/2021-2022/catalogo-general-2021-2022/courses/{re.escape(slug)}/\d{{4}}/[^"]+)"'
    paths = re.findall(pattern, html)
    # Deduplicate preserving order
    seen = set()
    result = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append((path.split("/")[-1].upper().replace("-", " ", 1), f"{BASE}{path}"))
    return result

def parse_course_page(html, url):
    """Extract title, credits, prereqs from course page HTML."""
    if not html:
        return None

    # Title from H1: <h1...><span>CODE</span> Title text</h1>
    m = re.search(r'<h1[^>]*>.*?<span>[^<]+</span>\s*(.*?)</h1>', html, re.DOTALL)
    if not m:
        return None
    title = html_module.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
    if not title:
        return None

    # Credits
    m = re.search(r'<div class="credits">\s*(\d+)\s*</div>', html)
    credits = int(m.group(1)) if m else 3

    # Prereqs from sc_prereqs div
    prereqs = []
    m = re.search(r'<div class="sc_prereqs">(.*?)</div>', html, re.DOTALL)
    if m:
        prereqs += re.findall(r"class='sc-courselink'[^>]*>([A-Z]{2,4}\s+\d{4})<", m.group(1))

    # Coreqs also treated as prereqs for sequencing purposes
    m = re.search(r'<div class="sc_coreqs">(.*?)</div>', html, re.DOTALL)
    if m:
        prereqs += re.findall(r"class='sc-courselink'[^>]*>([A-Z]{2,4}\s+\d{4})<", m.group(1))

    # Deduplicate
    seen = set()
    unique_prereqs = []
    for p in prereqs:
        if p not in seen:
            seen.add(p)
            unique_prereqs.append(p)

    return {"title": title, "credits": credits, "prereqs": unique_prereqs}

def scrape_dept(prefix, slug):
    """Scrape all courses for a department. Returns dict of {code: {title, credits, prereqs}}."""
    with print_lock:
        print(f"  [{prefix}] fetching listing...", flush=True)

    course_urls = get_course_urls_for_dept(prefix, slug)
    if not course_urls:
        with print_lock:
            print(f"  [{prefix}] no courses found", flush=True)
        return {}

    results = {}
    for raw_code, url in course_urls:
        # Parse code from URL: last segment like "biol-1101" -> "BIOL 1101"
        slug_part = url.split("/")[-1]
        m = re.match(r'^([a-z]+)-(\d+\w*)$', slug_part)
        if m:
            code = f"{m.group(1).upper()} {m.group(2)}"
        else:
            code = raw_code

        html = fetch(url)
        data = parse_course_page(html, url)
        if data:
            results[code] = data

    with print_lock:
        print(f"  [{prefix}] {len(results)} courses scraped", flush=True)
    return results

def yaml_entry(code, data):
    title_escaped = data["title"].replace('"', '\\"')
    prereqs_str = ", ".join(f'"{p}"' for p in data["prereqs"])
    prereqs_yaml = f"[{prereqs_str}]" if data["prereqs"] else "[]"
    return f'  {code}:\n    title: "{title_escaped}"\n    credits: {data["credits"]}\n    prereqs: {prereqs_yaml}\n'

def main():
    print(f"Scraping {len(DEPT_SLUGS)} departments...", flush=True)
    all_courses = {}

    # Use thread pool for parallel dept scraping
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(scrape_dept, prefix, slug): prefix
            for prefix, slug in DEPT_SLUGS.items()
        }
        for future in as_completed(futures):
            prefix = futures[future]
            try:
                dept_courses = future.result()
                all_courses.update(dept_courses)
            except Exception as e:
                with print_lock:
                    print(f"  [{prefix}] ERROR: {e}", flush=True)

    print(f"\nTotal courses scraped: {len(all_courses)}", flush=True)

    # Sort by prefix then number
    def sort_key(code):
        parts = code.split()
        num_str = re.sub(r'\D', '', parts[1]) if len(parts) > 1 else ''
        return (parts[0], int(num_str) if num_str else 0, parts[1] if len(parts) > 1 else '')

    sorted_codes = sorted(all_courses.keys(), key=sort_key)

    # Group by prefix for comments
    lines = [
        "# courses-2020-21.yaml — Course definitions for 2020-21 catalog year\n",
        "# Scraped from Inter American University 2021-2022 SmartCatalog\n",
        "# Format: CODE: { title, credits, prereqs[] }\n\n",
        "courses:\n\n",
    ]

    current_prefix = None
    for code in sorted_codes:
        prefix = code.split()[0]
        if prefix != current_prefix:
            lines.append(f"  # ── {prefix} {'─' * (50 - len(prefix))}\n")
            current_prefix = prefix
        lines.append(yaml_entry(code, all_courses[code]))

    out_path = "data/courses/courses-2020-21.yaml"
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Written: {out_path}", flush=True)

if __name__ == "__main__":
    main()
