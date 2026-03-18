/**
 * settling.js — Term-settling algorithm
 * Modified topological sort with credit packing.
 * Pure functions, no DOM access.
 */

/**
 * Settle courses into terms.
 *
 * @param {object[]} slots - Course slots from resolveSlots()
 * @param {object} config - { maxCreditsPerTerm, termsCount, termPins, userPins }
 * @returns {object[][]} Array of term arrays, each containing slot objects
 */
export function settle(slots, config) {
  const { maxCreditsPerTerm = 18, termsCount = 8, termPins = {}, userPins = {} } = config;

  // Build a set of all course codes in this degree
  const degreeCodes = new Set(slots.map(s => s.code));

  // Build prerequisite graph (only within-degree prereqs)
  const prereqMap = new Map();
  for (const slot of slots) {
    const relevant = (slot.prereqs || []).filter(p => degreeCodes.has(p));
    prereqMap.set(slot.code, relevant);
  }

  // Combine YAML term_pins and user drag-pins
  // User pins take precedence over YAML pins
  const pinned = new Map(); // code → term (0-indexed)
  for (const [termStr, codes] of Object.entries(termPins)) {
    const termIdx = parseInt(termStr, 10) - 1; // YAML uses 1-indexed
    for (const code of codes) {
      if (degreeCodes.has(code)) {
        pinned.set(code, termIdx);
      }
    }
  }
  for (const [code, termIdx] of Object.entries(userPins)) {
    if (degreeCodes.has(code)) {
      pinned.set(code, termIdx);
    }
  }

  // Compute earliest possible term for each course using Kahn's algorithm
  const inDegree = new Map();
  const dependents = new Map(); // code → [codes that depend on it]

  for (const slot of slots) {
    const prereqs = prereqMap.get(slot.code) || [];
    inDegree.set(slot.code, prereqs.length);
    for (const p of prereqs) {
      if (!dependents.has(p)) dependents.set(p, []);
      dependents.get(p).push(slot.code);
    }
  }

  const earliest = new Map();
  const queue = [];

  for (const slot of slots) {
    if (inDegree.get(slot.code) === 0) {
      earliest.set(slot.code, 0);
      queue.push(slot.code);
    }
  }

  // BFS to compute earliest term
  let qi = 0;
  while (qi < queue.length) {
    const code = queue[qi++];
    const deps = dependents.get(code) || [];
    for (const dep of deps) {
      const newEarliest = (earliest.get(code) || 0) + 1;
      earliest.set(dep, Math.max(earliest.get(dep) || 0, newEarliest));
      inDegree.set(dep, inDegree.get(dep) - 1);
      if (inDegree.get(dep) === 0) {
        queue.push(dep);
      }
    }
  }

  // Initialize term slots
  const terms = Array.from({ length: termsCount }, () => []);
  const termCredits = new Array(termsCount).fill(0);

  // Place pinned courses first
  const placed = new Set();
  for (const [code, termIdx] of pinned) {
    const slot = slots.find(s => s.code === code);
    if (!slot || termIdx >= termsCount) continue;
    terms[termIdx].push(slot);
    termCredits[termIdx] += slot.credits;
    placed.add(code);
  }

  // Sort unpinned slots by: earliest term, then priority, then code
  const unpinned = slots
    .filter(s => !placed.has(s.code))
    .sort((a, b) => {
      const ea = earliest.get(a.code) || 0;
      const eb = earliest.get(b.code) || 0;
      if (ea !== eb) return ea - eb;
      if (a.priority !== b.priority) return a.priority - b.priority;
      return a.code.localeCompare(b.code);
    });

  // Place unpinned courses
  for (const slot of unpinned) {
    const minTerm = earliest.get(slot.code) || 0;

    // Also ensure all prereqs are placed in earlier terms
    let prereqMaxTerm = 0;
    for (const p of (prereqMap.get(slot.code) || [])) {
      const pTerm = findTermOf(terms, p);
      if (pTerm !== null) {
        prereqMaxTerm = Math.max(prereqMaxTerm, pTerm + 1);
      }
    }

    let targetTerm = Math.max(minTerm, prereqMaxTerm);

    // Find first term with room
    while (targetTerm < termsCount && termCredits[targetTerm] + slot.credits > maxCreditsPerTerm) {
      targetTerm++;
    }

    // If we exceed terms count, just put in last term (overflow)
    if (targetTerm >= termsCount) {
      targetTerm = termsCount - 1;
    }

    terms[targetTerm].push(slot);
    termCredits[targetTerm] += slot.credits;
    placed.add(slot.code);
  }

  return terms;
}

/**
 * Find which term (0-indexed) a course is placed in
 */
function findTermOf(terms, code) {
  for (let t = 0; t < terms.length; t++) {
    if (terms[t].some(s => s.code === code)) return t;
  }
  return null;
}

/**
 * Validate placements — check no course is before its prereqs
 * @param {object[][]} terms
 * @returns {string[]} Array of violation messages (empty = valid)
 */
export function validatePlacements(terms) {
  const violations = [];
  const termOf = new Map();

  for (let t = 0; t < terms.length; t++) {
    for (const slot of terms[t]) {
      termOf.set(slot.code, t);
    }
  }

  for (let t = 0; t < terms.length; t++) {
    for (const slot of terms[t]) {
      for (const prereq of (slot.prereqs || [])) {
        const prereqTerm = termOf.get(prereq);
        if (prereqTerm !== undefined && prereqTerm >= t) {
          violations.push(
            `${slot.code} (term ${t + 1}) requires ${prereq} (term ${prereqTerm + 1})`
          );
        }
      }
    }
  }

  return violations;
}
