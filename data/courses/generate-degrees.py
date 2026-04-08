#!/usr/bin/env python3
"""
Generate degree YAML files from scraped SmartCatalog data.
Also identifies new courses not in courses-2025-26.yaml.
"""

import json
import yaml
import re
import sys
import os
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

ROOT = Path("C:/Users/paulw/curricular-sequence")

# Load scraped data
with open(ROOT / "data/extraction-notes/phase5-scraped-full.json", "r", encoding="utf-8") as f:
    scraped = json.load(f)

# Load existing courses
with open(ROOT / "data/courses/courses-2025-26.yaml", "r", encoding="utf-8") as f:
    courses_data = yaml.safe_load(f)
existing_courses = set(courses_data.get("courses", {}).keys())

# Load gen-ed templates to know which courses are gen-ed
with open(ROOT / "data/gen-ed/gen-ed-bachelor.yaml", "r", encoding="utf-8") as f:
    bachelor_gened = yaml.safe_load(f)
with open(ROOT / "data/gen-ed/gen-ed-associate.yaml", "r", encoding="utf-8") as f:
    associate_gened = yaml.safe_load(f)

def get_gened_courses(template):
    """Extract all course codes from a gen-ed template."""
    codes = set()
    for cat in template.get("categories", []):
        for c in cat.get("courses", []):
            codes.add(c)
        for sub in cat.get("subcategories", []):
            for c in sub.get("courses", []):
                codes.add(c)
            for c in sub.get("options", []):
                codes.add(c)
            if sub.get("default"):
                codes.add(sub["default"])
    return codes

bachelor_gened_courses = get_gened_courses(bachelor_gened)
associate_gened_courses = get_gened_courses(associate_gened)

# Degree type metadata
DEGREE_META = {
    # CHANGED
    "nursing-bsn": {"label": "Nursing (BSN)", "type": "bachelor", "terms": 8, "total": 120},
    "social-sciences-ba": {"label": "Social Sciences (BA)", "type": "bachelor", "terms": 8, "total": 121},
    "biomedical-sciences-bs": {"label": "Biomedical Sciences (BS)", "type": "bachelor", "terms": 8, "total": 121},
    "social-work-ba": {"label": "Social Work (BA)", "type": "bachelor", "terms": 8, "total": 120},
    "biology-bs": {"label": "Biology (BS)", "type": "bachelor", "terms": 8, "total": 123},
    "marine-sciences-bs": {"label": "Marine Sciences (BS)", "type": "bachelor", "terms": 8, "total": 128},
    "natural-sciences-bs": {"label": "Natural Sciences (BS)", "type": "bachelor", "terms": 8, "total": 120},
    "toxicology-bs": {"label": "Toxicology (BS)", "type": "bachelor", "terms": 8, "total": 123},
    "computer-science-aas": {"label": "Computer Science (AAS)", "type": "associate", "terms": 5, "total": 62},
    "agronomy-bas": {"label": "Agronomy (BAS)", "type": "bachelor", "terms": 8, "total": 129},
    "animal-science-pre-vet-bs": {"label": "Animal Science with Emphasis in Pre-Veterinary Science (BS)", "type": "bachelor", "terms": 8, "total": 120},
    "fine-arts-bfa": {"label": "Fine Arts (BFA)", "type": "bachelor", "terms": 8, "total": 142},
    "early-childhood-education-k5-ba": {"label": "Early Childhood Education: Elementary Level K-5 (BA)", "type": "bachelor", "terms": 8, "total": 127},
    # NEW
    "agricultural-precision-aas": {"label": "Precision Agriculture (AAS)", "type": "associate", "terms": 5, "total": 60},
    "cyber-security-bs": {"label": "Cyber Security (BS)", "type": "bachelor", "terms": 8, "total": 120},
    "electrical-engineering-technology-as": {"label": "Electrical Engineering Technology (AS)", "type": "associate", "terms": 5, "total": 68},
    "engineering-technology-renewable-energy-as": {"label": "Engineering Technology in Renewable Energy (AS)", "type": "associate", "terms": 5, "total": 68},
    "geomatics-civil-engineering-technology-as": {"label": "Geomatics and Civil Engineering Technology (AS)", "type": "associate", "terms": 5, "total": 68},
    "healthcare-billing-aa": {"label": "Billing of Healthcare Services (AA)", "type": "associate", "terms": 5, "total": 60},
    "integral-beauty-aa": {"label": "Integral Beauty (AA)", "type": "associate", "terms": 5, "total": 60},
    "molecular-medicine-bioprocesses-bs": {"label": "Molecular Medicine and Bioprocesses (BS)", "type": "bachelor", "terms": 8, "total": 120},
    "nursing-rn-to-bsn": {"label": "Nursing RN to BSN (BSN)", "type": "bachelor", "terms": 4, "total": 120},
    "renewable-energy-pv-aa": {"label": "Renewable Energy Technology with Photovoltaic Systems (AA)", "type": "associate", "terms": 5, "total": 60},
    "sports-technology-ba": {"label": "Sports Technology (BA)", "type": "bachelor", "terms": 8, "total": 120},
    "diagnostic-ultrasound-aas": {"label": "Ultrasound Diagnostic (AAS)", "type": "associate", "terms": 5, "total": 78},
    "veterinary-technician-aas": {"label": "Veterinary Technician (AAS)", "type": "associate", "terms": 5, "total": 60},
    "veterinary-technology-bs": {"label": "Veterinary Technology (BS)", "type": "bachelor", "terms": 8, "total": 120},
    "visual-arts-art-teaching-ba": {"label": "Visual Arts with Art Teaching (BA)", "type": "bachelor", "terms": 8, "total": 142},
    "early-childhood-education-pk4-ba": {"label": "Early Childhood Education: Preschool to Fourth Grade PK-4 (BA)", "type": "bachelor", "terms": 8, "total": 133},
    "physical-education-k12-ba": {"label": "Physical Education K-12 (BA)", "type": "bachelor", "terms": 8, "total": 130},
}

def classify_category(label):
    """Guess category_type from heading text."""
    low = label.lower()
    if "general education" in low or "gen ed" in low:
        return "gen-ed"
    if "major" in low or "concentration" in low or "specializ" in low:
        return "major"
    if "core" in low or "related" in low or "supporting" in low:
        return "core"
    if "distributive" in low or "prescribed" in low:
        return "distributive"
    if "elective" in low or "free" in low:
        return "elective"
    if "professional" in low or "pedagog" in low:
        return "core"
    return "major"  # default

def make_category_id(label):
    """Generate a slug from category label."""
    slug = re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')
    # Remove credit info from slug
    slug = re.sub(r'-?\d+(-\d+)?-credits?', '', slug).strip('-')
    return slug[:50]

def generate_degree_yaml(tid, info, meta):
    """Generate degree YAML content."""
    is_bachelor = meta["type"] == "bachelor"
    gened_template = "gen-ed-bachelor" if is_bachelor else "gen-ed-associate"
    gened_credits = 48 if is_bachelor else 24
    gened_courses = bachelor_gened_courses if is_bachelor else associate_gened_courses

    # Filter categories — skip gen-ed summary rows
    categories = []
    for cat in info.get("categories", []):
        label = cat["label"]
        low = label.lower()

        # Skip the top summary row and gen-ed categories
        if "general education" in low and "requirement" in low:
            continue
        if "requirements for the" in low or "requirements of the" in low:
            continue

        courses = [c for c in cat["courses"] if c not in gened_courses]
        if not courses and not cat.get("rows"):
            continue

        cat_type = classify_category(label)
        cat_id = make_category_id(label)

        # Parse credits from label
        credits = cat.get("credits")
        if not credits:
            m = re.search(r'(\d+(?:\s*[-\u2013]\s*\d+)?)\s*(?:credits?|cr)', label, re.I)
            if m:
                credits = m.group(1)

        # Detect if there are "or" choices in rows
        has_choices = False
        for row in cat.get("rows", []):
            if " or " in row.lower() or "choose" in row.lower() or "select" in row.lower():
                has_choices = True
                break

        entry = {
            "id": cat_id,
            "label": re.sub(r'\s*[-\u2013]\s*\d+(?:\s*[-\u2013]\s*\d+)?\s*(?:credits?|cr\.?)\s*$', '', label, flags=re.I).strip(),
            "credits": int(credits.split("-")[0].split("\u2013")[0].strip()) if credits else len(courses) * 3,
            "rule": "prereq-order",
            "category_type": cat_type,
            "courses": courses,
        }
        categories.append(entry)

    # Build YAML structure
    degree = {
        "id": tid,
        "label": meta["label"],
        "degree_type": meta["type"],
        "total_credits": meta["total"],
        "term_type": "semester",
        "max_credits_per_term": 18,
        "terms_count": meta["terms"],
        "gen_ed": {"template": gened_template},
        "categories": categories,
    }

    return degree

def to_yaml_str(degree):
    """Convert degree dict to YAML string with proper formatting."""
    lines = []
    lines.append(f"id: {degree['id']}")
    lines.append(f'label: "{degree["label"]}"')
    lines.append(f"degree_type: {degree['degree_type']}")
    lines.append(f"total_credits: {degree['total_credits']}")
    lines.append(f"term_type: {degree['term_type']}")
    lines.append(f"max_credits_per_term: {degree['max_credits_per_term']}")
    lines.append(f"terms_count: {degree['terms_count']}")
    lines.append("")
    lines.append("gen_ed:")
    lines.append(f"  template: {degree['gen_ed']['template']}")
    lines.append("")
    lines.append("categories:")

    for cat in degree["categories"]:
        lines.append(f"  - id: {cat['id']}")
        lines.append(f'    label: "{cat["label"]}"')
        lines.append(f"    credits: {cat['credits']}")
        lines.append(f"    rule: {cat['rule']}")
        lines.append(f"    category_type: {cat['category_type']}")
        if cat.get("courses"):
            lines.append("    courses:")
            for c in cat["courses"]:
                lines.append(f'      - "{c}"')
        lines.append("")

    lines.append("# TODO: term_pins \u2014 no recommended sequence available from catalog.")
    lines.append("# Obtain from academic advisor or departmental curricular sequence document.")

    return "\n".join(lines) + "\n"

def main():
    new_courses = set()
    generated = []
    skipped = []

    for tid, info in sorted(scraped["results"].items()):
        meta = DEGREE_META.get(tid)
        if not meta:
            skipped.append(tid)
            continue

        # Collect all courses from this degree
        for code in info["all_courses"]:
            if code not in existing_courses:
                new_courses.add(code)

        # Generate YAML
        degree = generate_degree_yaml(tid, info, meta)
        yaml_str = to_yaml_str(degree)

        # Write file
        outpath = ROOT / "data" / "degrees" / "2025-26" / f"{tid}.yaml"
        outpath.parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(yaml_str)

        generated.append(tid)
        cat_count = len(degree["categories"])
        course_count = sum(len(c.get("courses", [])) for c in degree["categories"])
        print(f"  {tid}: {cat_count} categories, {course_count} courses", file=sys.stderr)

    # Report
    print(f"\n=== Generated {len(generated)} degree YAMLs ===", file=sys.stderr)
    if skipped:
        print(f"Skipped (no metadata): {skipped}", file=sys.stderr)

    print(f"\n=== {len(new_courses)} courses not in courses-2025-26.yaml ===", file=sys.stderr)

    # Output new courses as JSON for further processing
    output = {
        "generated": generated,
        "new_courses": sorted(new_courses),
        "new_course_links": {},
    }

    # Collect course links for new courses
    for tid, info in scraped["results"].items():
        for code, link in info.get("all_courses_with_links", {}).items():
            if code in new_courses:
                output["new_course_links"][code] = link

    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
