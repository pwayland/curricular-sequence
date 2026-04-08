"""
generate-intermediary-years.py
Adds missing non-business degrees to 2022-23, 2023-24, 2024-25 in catalog-years.yaml.
Those years already have 29 business-school degrees from Phase 4.
This script appends all remaining 2020-21 degrees with correct aliasing.

Aliasing logic for the 13 "changed" degrees (verified against 2022-23 catalog):
  → 2025-26: biomedical-sciences-bs, animal-science-with-pre-veterinary-bs,
             social-sciences-ba
  → 2020-21: all other changed degrees (nursing-bsn, biology-bs, marine-sciences-bs,
             natural-sciences-bs, toxicology-bs, agronomy-bas, social-work-ba,
             computer-science-aas, early-childhood-education-k3-ba, fine-arts-bfa)

Special canonical 2022-23 files:
  entrepreneurial-and-managerial-development-bba  (already in 2022-23 as file:)
  organizational-behavior-bba  (already in 2022-23 as file:)
"""

import yaml, re

CATALOG_PATH = 'data/catalog-years.yaml'

# Degrees that alias to 2025-26 instead of 2020-21
TO_2025_26 = {
    'biomedical-sciences-bs',
    'animal-science-with-pre-veterinary-bs',
    'social-sciences-ba',
}

def load_yaml_with_comments(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def get_year_data(data, year_id):
    return next((y for y in data['years'] if y['id'] == year_id), None)

def get_existing_ids(year_data):
    return {d['id'] for d in year_data['degrees']}

def build_new_entries(year_id, degrees_2020, existing_ids):
    """Returns list of new degree entry dicts to append."""
    entries = []
    for d in degrees_2020:
        did = d['id']
        label = d['label']

        # Skip if already present
        if did in existing_ids:
            continue

        if did in TO_2025_26:
            entries.append({'id': did, 'label': label, 'alias_of': f'2025-26/{did}'})
        elif did == 'entrepreneurial-and-managerial-development-bba':
            # v2 canonical is in 2022-23
            if year_id == '2022-23':
                # Should already be there from Phase 4, but just in case
                entries.append({'id': did, 'label': label, 'file': f'degrees/2022-23/{did}.yaml'})
            else:
                entries.append({'id': did, 'label': label, 'alias_of': f'2022-23/{did}'})
        else:
            entries.append({'id': did, 'label': label, 'alias_of': f'2020-21/{did}'})

    return entries

def entry_to_yaml(entry, indent=6):
    sp = ' ' * indent
    lines = [f'{sp}- id: {entry["id"]}']
    lines.append(f'{sp}  label: "{entry["label"]}"')
    if 'file' in entry:
        lines.append(f'{sp}  file: {entry["file"]}')
    elif 'alias_of' in entry:
        lines.append(f'{sp}  alias_of: {entry["alias_of"]}')
    return '\n'.join(lines)

# Load data
raw = load_yaml_with_comments(CATALOG_PATH)
data = yaml.safe_load(raw)

year_2020 = get_year_data(data, '2020-21')

total_added = 0
for year_id in ['2022-23', '2023-24', '2024-25']:
    year_data = get_year_data(data, year_id)
    existing_ids = get_existing_ids(year_data)
    new_entries = build_new_entries(year_id, year_2020['degrees'], existing_ids)

    print(f'{year_id}: {len(existing_ids)} existing, adding {len(new_entries)} new')
    total_added += len(new_entries)

    # Append new entries to the year's degrees list in the parsed data
    year_data['degrees'].extend(new_entries)

print(f'\nTotal new entries across all 3 years: {total_added}')

# Write back — use PyYAML dump but preserve header comments manually
header_end = raw.find('\nyears:')
header = raw[:header_end + 1]  # keep everything up to and including newline before 'years:'

# Dump just the years portion with custom settings
class LiteralStr(str): pass

def represent_literal(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(LiteralStr, represent_literal)

# Custom dumper to control formatting
class MyDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, indentless=False)

output_data = yaml.dump(
    data,
    Dumper=MyDumper,
    default_flow_style=False,
    allow_unicode=True,
    sort_keys=False,
    width=120
)

# Write final file
with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
    f.write(header)
    f.write('years:\n')
    # Write each year manually to preserve formatting
    for year in data['years']:
        f.write(f'  - id: {year["id"]}\n')
        f.write(f'    label: {year["label"]}\n')
        f.write(f'    courses_file: {year["courses_file"]}\n')
        f.write(f'    degrees:\n')
        for d in year['degrees']:
            f.write(f'      - id: {d["id"]}\n')
            f.write(f'        label: "{d["label"]}"\n')
            if 'file' in d:
                f.write(f'        file: {d["file"]}\n')
            elif 'alias_of' in d:
                f.write(f'        alias_of: {d["alias_of"]}\n')

print(f'\nUpdated {CATALOG_PATH}')
