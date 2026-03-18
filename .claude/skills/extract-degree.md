---
name: extract-degree
description: Extract a degree program from Inter's SmartCatalog and convert it to the project's YAML data format
user_invocable: true
---

# Extract Degree from SmartCatalog

You are extracting a degree program from Inter American University's SmartCatalog website and converting it into YAML files for the curricular-sequence project.

## Input

The user provides a SmartCatalog URL like:
`https://inter.smartcatalogiq.com/en/YYYY-YYYY/general-catalog-YYYY-YYYY/programs-of-study.../degree-name`

## Steps

### 1. Determine the catalog year

Parse the URL to extract the catalog year (e.g., `2025-2026` → `2025-26`). Verify this year exists in `data/catalog-years.yaml`. If not, inform the user they need to create the year entry first.

### 2. Fetch the program page

Use WebFetch to fetch the catalog URL. Extract:
- Degree name and type (BS, BA, BBA, AS, AA, etc.)
- Total credits
- All course categories with their courses, grouped as shown on the page
- Any notes about tracks, elective choices, or special requirements

### 3. Identify all unique course codes

Compile a list of every course code mentioned in the program. Check `data/courses/courses-{year}.yaml` to see which courses already exist.

### 4. Scrape prerequisites for new courses

For each course NOT already in the courses file, fetch its SmartCatalog course description page to extract prerequisites. The URL pattern is:
```
https://inter.smartcatalogiq.com/en/{year}/general-catalog-{year}/courses/{dept-slug}/{level}/{course-code}
```

The department slug can be found by fetching the courses index:
```
https://inter.smartcatalogiq.com/en/{year}/general-catalog-{year}/courses
```

If the direct URL 404s, try adding a numeric level segment (1000, 2000, 3000, 4000) between the department and course code.

For "or" prerequisites (e.g., "OMSY 1101 or GEIC 1010"), use the prerequisite that appears in this degree's curriculum or gen-ed template.

### 5. Add new courses to the courses file

Append new course entries to `data/courses/courses-{year}.yaml` following the existing format:
```yaml
  DEPT CODE:
    title: "Full Course Title"
    credits: N
    prereqs: ["PREREQ 1", "PREREQ 2"]  # or [] if none
```

Group courses by department with section comment headers matching the existing style.

### 6. Create the degree YAML file

Create `data/degrees/{year}/{degree-id}.yaml` following this structure:

```yaml
id: {degree-id}
label: "{Degree Name} ({Type})"
degree_type: bachelor  # or associate
total_credits: N
term_type: semester
max_credits_per_term: 18
terms_count: 8  # 8 for bachelor, 4-5 for associate

gen_ed:
  template: gen-ed-bachelor  # or gen-ed-associate

categories:
  # Map each program section to a category with appropriate rule type
```

**Category mapping rules:**
- Courses with no choices → `rule: prereq-order` (lets the settling algorithm order by prereqs)
- "Choose one of..." → `rule: pick` with `pick_count` and `options`
- Ordered sequences → `rule: sequence`
- Free/open electives → `rule: open-elective`
- Fixed courses with no prereqs → `rule: fixed`

**Category type mapping:**
- General Education → `category_type: gen-ed` (handled by template)
- Core Requirements → `category_type: core`
- Major Requirements → `category_type: major`
- Related/Distributive → `category_type: distributive`
- Electives → `category_type: elective`

**Repeatable courses** (e.g., "Special Topics" taken 3 times): Create numbered variants (e.g., MUBA 3971, MUBA 3972, MUBA 3973) and use `rule: fixed`.

**Term pins**: Do NOT generate term_pins. Add this comment at the end:
```yaml
# TODO: term_pins — no recommended sequence available from catalog.
# Obtain from academic advisor or departmental curricular sequence document.
```

### 7. Update catalog-years.yaml

Add the degree entry under the appropriate year:
```yaml
      - id: {degree-id}
        label: "{Degree Name} ({Type})"
        file: "degrees/{year}/{degree-id}.yaml"
```

### 8. Verify

- Start the dev server if not running
- Select the catalog year and new degree in the UI
- Check for console errors
- Verify all categories render with correct courses
- Verify pick dropdowns work
- Report the prereq violation warnings (expected without term_pins)

### 9. Report

Summarize:
- Courses added (with prereqs found/not found)
- Categories created
- Any issues or ambiguities found
- Remind user that term_pins need to be added from an advisor source

## Credit Verification

The sum of all category credits + gen-ed credits must equal total_credits:
- Bachelor gen-ed = 48 credits
- Associate gen-ed = 24 credits

If the numbers don't add up, flag the discrepancy to the user.

## Cross-Year Aliasing

If the user mentions that a program is identical across years, add an `alias_of` entry instead of duplicating the degree file:
```yaml
      - id: {degree-id}
        label: "{Degree Name} ({Type})"
        alias_of: "{source-year}/{degree-id}"
```
