/**
 * yaml-loader.js — Fetch, parse, and merge YAML data files
 * Uses the global jsyaml object from the vendored js-yaml library.
 */

const DATA_BASE = 'data/';

/**
 * Fetch and parse a YAML file relative to data/
 * @param {string} path - Path relative to data/ directory
 * @returns {Promise<object>}
 */
export async function loadYaml(path) {
  const url = DATA_BASE + path;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to load ${url}: ${resp.status}`);
  const text = await resp.text();
  return jsyaml.load(text);
}

/**
 * Load the master catalog-years index
 * @returns {Promise<object[]>} Array of year objects
 */
export async function loadCatalogYears() {
  const data = await loadYaml('catalog-years.yaml');
  return data.years || [];
}

/**
 * Load course definitions for a catalog year
 * @param {string} coursesFile - Relative path to courses YAML
 * @returns {Promise<Map<string, object>>} Map of course code → course data
 */
export async function loadCourses(coursesFile) {
  const data = await loadYaml(coursesFile);
  return new Map(Object.entries(data.courses || {}));
}

/**
 * Load a gen-ed template
 * @param {string} templateId - e.g. "gen-ed-bachelor"
 * @returns {Promise<object>}
 */
export async function loadGenEdTemplate(templateId) {
  const path = `gen-ed/${templateId}.yaml`;
  return loadYaml(path);
}

/**
 * Load a degree file
 * @param {string} degreeFile - Relative path to degree YAML
 * @returns {Promise<object>}
 */
export async function loadDegree(degreeFile) {
  return loadYaml(degreeFile);
}

/**
 * Resolve a degree entry's file path, following alias_of if present.
 * When alias_of is set, the degree points to another year's version
 * (e.g. "2025-26/computer-science-bs").
 * @param {object} degreeEntry - Degree entry from catalog-years.yaml
 * @param {object[]} allYears - All year entries from catalog-years.yaml
 * @returns {{ file: string, aliasOf: string|null, aliasYear: object|null }}
 */
export function resolveDegreeAlias(degreeEntry, allYears) {
  if (!degreeEntry.alias_of) {
    return { file: degreeEntry.file, aliasOf: null, aliasYear: null };
  }

  // alias_of format: "yearId/degreeId"
  const [yearId, degreeId] = degreeEntry.alias_of.split('/');
  const targetYear = allYears.find(y => y.id === yearId);
  if (!targetYear) {
    throw new Error(`Alias target year "${yearId}" not found`);
  }

  const targetDegree = targetYear.degrees.find(d => d.id === degreeId);
  if (!targetDegree) {
    throw new Error(`Alias target degree "${degreeId}" not found in year "${yearId}"`);
  }

  // Recursively resolve in case the target is also an alias
  const resolved = resolveDegreeAlias(targetDegree, allYears);
  return {
    file: resolved.file,
    aliasOf: degreeEntry.alias_of,
    aliasYear: targetYear,
  };
}

/**
 * Deep-merge gen-ed overrides onto a template.
 * Override rules:
 *   - Scalar properties (credits, default, etc.) are replaced
 *   - _remove: true deletes the category entirely
 *   - subcategories as array = full replacement
 *   - subcategories as object keyed by id = targeted merge
 * @param {object} template - Gen-ed template
 * @param {object} overrides - Degree's gen_ed.overrides
 * @returns {object} Merged gen-ed config
 */
export function mergeGenEd(template, overrides) {
  if (!overrides) return template;

  const result = structuredClone(template);

  for (const [catId, overrideVal] of Object.entries(overrides)) {
    const catIdx = result.categories.findIndex(c => c.id === catId);
    if (catIdx === -1) continue;

    // Remove category entirely
    if (overrideVal._remove) {
      result.categories.splice(catIdx, 1);
      continue;
    }

    const cat = result.categories[catIdx];

    // Merge subcategories
    if (overrideVal.subcategories) {
      if (Array.isArray(overrideVal.subcategories)) {
        // Full replacement
        cat.subcategories = overrideVal.subcategories;
      } else {
        // Object-keyed targeted merge
        for (const [subId, subOverride] of Object.entries(overrideVal.subcategories)) {
          if (!cat.subcategories) continue;
          const subIdx = cat.subcategories.findIndex(s => s.id === subId);
          if (subIdx === -1) continue;
          if (subOverride._remove) {
            cat.subcategories.splice(subIdx, 1);
          } else {
            Object.assign(cat.subcategories[subIdx], subOverride);
          }
        }
      }
    }

    // Merge scalar properties
    for (const [key, val] of Object.entries(overrideVal)) {
      if (key === 'subcategories' || key === '_remove') continue;
      cat[key] = val;
    }
  }

  return result;
}

/**
 * Resolve all courses for a degree: gen-ed + degree categories.
 * Returns a flat list of "slots" — each slot is a course to place,
 * with metadata about its category and rule.
 *
 * @param {object} degree - Parsed degree config
 * @param {object} genEd - Merged gen-ed config
 * @param {Map<string, object>} coursesMap - Course definitions
 * @param {object} userSelections - User's pick/track selections
 * @returns {object[]} Array of course slot objects
 */
export function resolveSlots(degree, genEd, coursesMap, userSelections = {}) {
  const slots = [];
  let priority = 0;

  // Resolve gen-ed categories
  for (const cat of genEd.categories) {
    if (cat.subcategories) {
      for (const sub of cat.subcategories) {
        resolveCategory(sub, cat.category_type || 'gen-ed', priority, slots, coursesMap, userSelections);
      }
    } else {
      resolveCategory(cat, cat.category_type || 'gen-ed', priority, slots, coursesMap, userSelections);
    }
    priority++;
  }

  // Resolve degree-specific categories
  for (const cat of (degree.categories || [])) {
    resolveCategory(cat, cat.category_type || 'major', priority, slots, coursesMap, userSelections);
    priority++;
  }

  return slots;
}

/**
 * Resolve a single category into course slots
 */
function resolveCategory(cat, categoryType, priority, slots, coursesMap, userSelections) {
  const selKey = cat.id;

  switch (cat.rule) {
    case 'fixed':
    case 'sequence':
      for (let i = 0; i < (cat.courses || []).length; i++) {
        const code = cat.courses[i];
        const course = coursesMap.get(code);
        if (!course) continue;
        slots.push({
          code,
          title: course.title,
          credits: course.credits,
          prereqs: course.prereqs || [],
          categoryId: cat.id,
          categoryLabel: cat.label,
          categoryType,
          rule: cat.rule,
          sequenceIndex: cat.rule === 'sequence' ? i : null,
          priority,
        });
      }
      break;

    case 'pick': {
      const count = cat.pick_count || 1;
      for (let i = 0; i < count; i++) {
        const selected = userSelections[`${selKey}_${i}`] || cat.default || cat.options[0];
        const course = coursesMap.get(selected);
        slots.push({
          code: selected,
          title: course ? course.title : selected,
          credits: course ? course.credits : 3,
          prereqs: course ? (course.prereqs || []) : [],
          categoryId: cat.id,
          categoryLabel: cat.label,
          categoryType,
          rule: 'pick',
          pickOptions: cat.options,
          pickIndex: i,
          priority,
        });
      }
      break;
    }

    case 'choose_track': {
      const trackName = userSelections[selKey] || cat.default_track;
      const trackCourses = cat.choose_track[trackName] || [];
      for (let i = 0; i < trackCourses.length; i++) {
        const code = trackCourses[i];
        const course = coursesMap.get(code);
        if (!course) continue;
        slots.push({
          code,
          title: course.title,
          credits: course.credits,
          prereqs: course.prereqs || [],
          categoryId: cat.id,
          categoryLabel: cat.label,
          categoryType,
          rule: 'choose_track',
          trackName,
          trackOptions: Object.keys(cat.choose_track),
          sequenceIndex: i,
          priority,
        });
      }
      break;
    }

    case 'prereq-order':
      for (const code of (cat.courses || [])) {
        const course = coursesMap.get(code);
        if (!course) continue;
        slots.push({
          code,
          title: course.title,
          credits: course.credits,
          prereqs: course.prereqs || [],
          categoryId: cat.id,
          categoryLabel: cat.label,
          categoryType,
          rule: 'prereq-order',
          priority,
        });
      }
      break;

    case 'open-elective': {
      const numCredits = cat.credits || 9;
      const count = cat.count || (5 + Math.floor(numCredits / 3));
      for (let i = 0; i < count; i++) {
        const userVal = userSelections[`${selKey}_elective_${i}`] || '';
        slots.push({
          code: userVal || `Elective ${i + 1}`,
          title: userVal ? '' : 'Open Elective',
          credits: 3,
          prereqs: [],
          categoryId: cat.id,
          categoryLabel: cat.label,
          categoryType: 'elective',
          rule: 'open-elective',
          electiveIndex: i,
          priority: priority + 100, // Electives settle last
        });
      }
      break;
    }

    default:
      // Unknown rule — treat as prereq-order
      for (const code of (cat.courses || [])) {
        const course = coursesMap.get(code);
        if (!course) continue;
        slots.push({
          code,
          title: course.title,
          credits: course.credits,
          prereqs: course.prereqs || [],
          categoryId: cat.id,
          categoryLabel: cat.label,
          categoryType,
          rule: cat.rule || 'prereq-order',
          priority,
        });
      }
  }
}
