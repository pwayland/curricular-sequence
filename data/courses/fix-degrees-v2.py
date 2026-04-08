#!/usr/bin/env python3
"""
Fix degree YAMLs v2:
- Add open-elective categories for positive credit gaps
- Adjust total_credits for negative gaps (scraped total was more accurate)
- Handle special cases manually
"""

import yaml
import sys
import os
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

ROOT = Path("C:/Users/paulw/curricular-sequence")

# Manual total_credits corrections based on scraped page data
# Format: id -> (total_credits, notes)
TOTAL_FIXES = {
    # Scraped totals that were more accurate than my guesses
    "biomedical-sciences-bs": (121, None),  # 48 + 57 + 12 = 117, some prescribed distributive overlap
    "cyber-security-bs": (129, None),  # 48 + 58 + 4 + 19 = 129
    "diagnostic-ultrasound-aas": (67, None),  # 24 + 43 = 67 (common for health AAS)
    "integral-beauty-aa": (65, None),  # 24 + 41 = 65
    "molecular-medicine-bioprocesses-bs": (132, None),  # 48 + 33 + 51 = 132
    "animal-science-pre-vet-bs": (129, None),  # 48 + 44 + 3 + 34 = 129
    "early-childhood-education-pk4-ba": (126, None),  # 48 + 78 = 126
    "visual-arts-art-teaching-ba": (133, None),  # 48 + 85 = 133
    "natural-sciences-bs": (120, None),  # keep 120, gap is electives
}

# Degrees that need restructuring (skip auto-fix, add TODO)
SKIP_AUTO = {
    "fine-arts-bfa",  # Track-based (Ceramics/Drawing/Sculpture/Photography/Painting/Teaching Art)
    "physical-education-k12-ba",  # Multiple concentration sections
    "social-sciences-ba",  # Under-scraped, only 7 courses
    "nursing-rn-to-bsn",  # RN completion program, different structure
}

def fix_degree(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    if not d:
        return

    tid = d["id"]

    if tid in SKIP_AUTO:
        print(f"  SKIP (needs manual): {tid}", file=sys.stderr)
        return

    # Fix total_credits if we have a correction
    if tid in TOTAL_FIXES:
        new_total, note = TOTAL_FIXES[tid]
        d["total_credits"] = new_total
        print(f"  Fixed total: {tid} -> {new_total}", file=sys.stderr)

    # Calculate gap
    is_bachelor = d.get("degree_type") == "bachelor"
    gened = 48 if is_bachelor else 24
    cat_cr = sum(c.get("credits", 0) for c in d.get("categories", []))
    total = d.get("total_credits", 0)
    gap = total - gened - cat_cr

    # Add open-elective if positive gap > 2
    if gap > 2:
        # Check if elective category already exists
        has_elective = any(c.get("category_type") == "elective" for c in d["categories"])
        if not has_elective:
            d["categories"].append({
                "id": "electives",
                "label": "Elective Courses",
                "credits": gap,
                "rule": "open-elective",
                "category_type": "elective",
            })
            print(f"  Added {gap}cr electives to {tid}", file=sys.stderr)

    # Write back
    write_degree(filepath, d)

def write_degree(filepath, d):
    lines = []
    lines.append(f"id: {d['id']}")
    lines.append(f'label: "{d["label"]}"')
    lines.append(f"degree_type: {d['degree_type']}")
    lines.append(f"total_credits: {d['total_credits']}")
    lines.append(f"term_type: {d['term_type']}")
    lines.append(f"max_credits_per_term: {d['max_credits_per_term']}")
    lines.append(f"terms_count: {d['terms_count']}")
    lines.append("")
    lines.append("gen_ed:")
    lines.append(f"  template: {d['gen_ed']['template']}")
    lines.append("")
    lines.append("categories:")

    for cat in d["categories"]:
        lines.append(f"  - id: {cat['id']}")
        lines.append(f'    label: "{cat["label"]}"')
        lines.append(f"    credits: {cat['credits']}")
        lines.append(f"    rule: {cat['rule']}")
        lines.append(f"    category_type: {cat['category_type']}")
        if cat.get("pick_count"):
            lines.append(f"    pick_count: {cat['pick_count']}")
        if cat.get("courses"):
            lines.append("    courses:")
            for c in cat["courses"]:
                lines.append(f'      - "{c}"')
        if cat.get("options"):
            lines.append("    options:")
            for o in cat["options"]:
                lines.append(f'      - "{o}"')
        lines.append("")

    lines.append("# TODO: term_pins \u2014 no recommended sequence available from catalog.")
    lines.append("# Obtain from academic advisor or departmental curricular sequence document.")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def main():
    degrees_dir = ROOT / "data/degrees/2025-26"
    skip = {"computer-science-bs.yaml", "corporate-communication-ba.yaml"}

    for f in sorted(degrees_dir.glob("*.yaml")):
        if f.name in skip:
            continue
        fix_degree(f)

    # Final credit check
    print("\n=== Final credit check ===", file=sys.stderr)
    for f in sorted(degrees_dir.glob("*.yaml")):
        if f.name in skip:
            continue
        with open(f, "r", encoding="utf-8") as fh:
            d = yaml.safe_load(fh)
        cat_cr = sum(c.get("credits", 0) for c in d.get("categories", []))
        ge = 48 if d.get("degree_type") == "bachelor" else 24
        total = d.get("total_credits", 0)
        gap = total - ge - cat_cr
        flag = " !!!" if abs(gap) > 6 else ""
        status = "OK" if abs(gap) <= 6 else "NEEDS WORK"
        print(f"  {status:10s} {d['id']:50s} total={total:3d} gap={gap:+4d}{flag}", file=sys.stderr)

if __name__ == "__main__":
    main()
