# Pickup Prompt — Catalog Completion

Copy-paste the section below into a new conversation:

---

## Context

I'm completing the curricular-sequence catalog. Phase 0 (web scraping) is done — raw degree data from SmartCatalog is saved in `data/extraction-notes/`. Here's where we are:

### Completed
- **2020-21 extraction**: ~105 degrees scraped from the 2021-2022 SmartCatalog into 5 files:
  - `2020-21-sciences.md` (19 degrees)
  - `2020-21-engineering-cs.md` (20 degrees)
  - `2020-21-health.md` (15 degrees)
  - `2020-21-social-education-misc.md` (30+ degrees incl education sub-programs)
  - `2020-21-arts-humanities.md` (20 degrees incl music sub-programs)
- **Existing 2020-21**: 30 degree YAML files already exist (all Business school)
- **Existing 2025-26**: 2 degree YAML files (computer-science-bs, corporate-communication-ba)

### Remaining work (in order)

**Phase 1: Check existing courses** — Compare course codes from extraction notes against `data/courses/courses-2025-26.yaml` to see how many already exist vs need prereq scraping.

**Phase 2: Batch prereq scraping** — For new courses, fetch department listing pages from SmartCatalog (one per dept, ~40 depts) rather than individual course pages (~500).

**Phase 3: Generate 2020-21 degree YAMLs** — Use Sonnet agents in batches of 15-20 to write degree YAML files from the extraction notes.

**Phase 4: 2021-22 aliases** — Add `alias_of: 2020-21/slug` entries to catalog-years.yaml for all ~105 new degrees.

**Phase 5: 2025-26 extraction** — Fetch the 2025-26 programs index from `https://inter.smartcatalogiq.com/en/2025-2026/general-catalog-2025-2026/programs-of-study-undergraduate-associate-and-bachelor-s-degree-programs`, compare slugs to 2020-21, only fetch pages for degrees that might differ.

**Phase 6: Fill intermediary years** — Where 2025-26 == 2020-21, add aliases for 2022-23, 2023-24, 2024-25. Where different, leave blank.

**Phase 7: Gap report** — List: (a) 2020-21 degrees without 2025-26 matches, (b) 2025-26 degrees without 2020-21 matches, (c) matching degrees that differ.

### Token efficiency notes
- Use Sonnet for mechanical file writing (Phases 3-4)
- Use Opus for comparison/judgment (Phases 5-7)
- Batch prereq scraping by department, not individual course
- The extract-degree skill is at `.claude/skills/extract-degree.md`

**Start with Phase 1** — read the extraction notes and the courses file to figure out how many new courses need prereq scraping.
