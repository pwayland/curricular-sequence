#!/usr/bin/env python3
"""Copy courses from 2020-21 to 2025-26 that are needed by the new degrees."""

import json, yaml, sys, os
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

ROOT = Path("C:/Users/paulw/curricular-sequence")

# Load needed courses
with open(ROOT / "data/extraction-notes/phase5-generation.json", "r", encoding="utf-8") as f:
    gen = json.load(f)
needed = set(gen["new_courses"])

# Load 2020-21
with open(ROOT / "data/courses/courses-2020-21.yaml", "r", encoding="utf-8") as f:
    c20 = yaml.safe_load(f)
courses_20 = c20.get("courses", {})

# Load 2025-26
with open(ROOT / "data/courses/courses-2025-26.yaml", "r", encoding="utf-8") as f:
    c25_text = f.read()
with open(ROOT / "data/courses/courses-2025-26.yaml", "r", encoding="utf-8") as f:
    c25 = yaml.safe_load(f)
courses_25 = c25.get("courses", {})

# Find courses to copy
to_copy = {}
for code in sorted(needed):
    if code in courses_25:
        continue
    if code in courses_20:
        to_copy[code] = courses_20[code]

print(f"Copying {len(to_copy)} courses from 2020-21 to 2025-26", file=sys.stderr)

# Group by department
by_dept = {}
for code, info in to_copy.items():
    dept = code.split()[0]
    if dept not in by_dept:
        by_dept[dept] = []
    by_dept[dept].append((code, info))

# Generate YAML to append
lines = ["\n  # === Courses copied from 2020-21 (Phase 5) ==="]
for dept in sorted(by_dept.keys()):
    lines.append(f"\n  # {dept}")
    for code, info in sorted(by_dept[dept]):
        title = info.get("title", "")
        credits = info.get("credits", 3)
        prereqs = info.get("prereqs", [])
        lines.append(f"  {code}:")
        lines.append(f'    title: "{title}"')
        lines.append(f"    credits: {credits}")
        if prereqs:
            prereq_str = ", ".join(f'"{p}"' for p in prereqs)
            lines.append(f"    prereqs: [{prereq_str}]")
        else:
            lines.append(f"    prereqs: []")

yaml_block = "\n".join(lines) + "\n"

# Append to courses file (before the final line if needed)
with open(ROOT / "data/courses/courses-2025-26.yaml", "a", encoding="utf-8") as f:
    f.write(yaml_block)

print(f"Done. Appended {len(to_copy)} courses.", file=sys.stderr)

# Report which courses are truly new
truly_new = sorted(c for c in needed if c not in courses_25 and c not in courses_20)
print(f"\nTruly new courses (not in 2020-21): {len(truly_new)}", file=sys.stderr)
for c in truly_new:
    link = gen.get("new_course_links", {}).get(c, "")
    print(f"  {c}  {link}", file=sys.stderr)
