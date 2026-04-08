#!/usr/bin/env python3
"""
Fix generated degree YAMLs:
1. Remove gen-ed courses from non-gened categories
2. Remove gen-ed heading categories (handled by template)
3. Remove minor/concentration overlap sections
4. Fix credit calculations
"""

import yaml
import re
import sys
import os
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

ROOT = Path("C:/Users/paulw/curricular-sequence")

# Load gen-ed courses
with open(ROOT / "data/gen-ed/gen-ed-bachelor.yaml", "r", encoding="utf-8") as f:
    bg = yaml.safe_load(f)
with open(ROOT / "data/gen-ed/gen-ed-associate.yaml", "r", encoding="utf-8") as f:
    ag = yaml.safe_load(f)

def get_gened_courses(template):
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

bachelor_gened = get_gened_courses(bg)
associate_gened = get_gened_courses(ag)

# Common gen-ed adjacent courses
GENED_ADJACENT = {"GESP 1101", "GESP 1102", "GEEN 1101", "GEEN 1102", "GEEN 1103",
    "GEHS 2010", "GEMA 1200", "GEMA 1000", "GEIC 1010", "GEHP 3000", "GECF 1000",
    "GEPE 1020", "GEED 2000", "GESO 1010"}

def fix_degree(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    d = yaml.safe_load(content)
    if not d:
        return False

    is_bachelor = d.get("degree_type") == "bachelor"
    gened = bachelor_gened if is_bachelor else associate_gened
    gened_credits = 48 if is_bachelor else 24

    changed = False
    new_cats = []

    for cat in d.get("categories", []):
        label = cat.get("label", "").lower()

        # Skip gen-ed summary categories
        if "general education" in label and ("requirement" in label or "credit" in label):
            changed = True
            continue

        # Skip "Requirements for the..." summary headers
        if label.startswith("requirements for") or label.startswith("academic requirements"):
            changed = True
            continue

        # Skip minor sections
        if "minor" in label and "courses for" in label:
            changed = True
            continue

        # Filter gen-ed courses from non-gened categories
        if cat.get("category_type") != "gen-ed":
            filtered = [c for c in cat.get("courses", []) if c not in gened and c not in GENED_ADJACENT]
            if len(filtered) < len(cat.get("courses", [])):
                removed = len(cat.get("courses", [])) - len(filtered)
                print(f"  Removed {removed} gen-ed courses from {cat['id']}", file=sys.stderr)
                cat["courses"] = filtered
                changed = True

        new_cats.append(cat)

    d["categories"] = new_cats

    if changed:
        # Rewrite
        write_degree(filepath, d)
    return changed

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
        print(f"Fixing {f.name}...", file=sys.stderr)
        fix_degree(f)

    # Recheck credits
    print("\n=== Credit check after fixes ===", file=sys.stderr)
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
        print(f"  {d['id']:50s} total={total:3d} gened={ge:2d} cats={cat_cr:3d} gap={gap:+4d}{flag}", file=sys.stderr)

if __name__ == "__main__":
    main()
