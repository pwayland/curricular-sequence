/**
 * renderer.js — DOM rendering for the term grid
 */

import { initDrag } from './drag.js';

const GRADES = ['', 'A', 'B+', 'B', 'C+', 'C', 'D', 'F', 'W', 'WF', 'WN', 'IP', 'T'];

const CATEGORY_COLORS = {
  'gen-ed': { label: 'General Education', color: 'var(--cat-gen-ed)' },
  'core': { label: 'Core', color: 'var(--cat-core)' },
  'major': { label: 'Major', color: 'var(--cat-major)' },
  'distributive': { label: 'Prescribed Distributive', color: 'var(--cat-distributive)' },
  'elective': { label: 'Electives', color: 'var(--cat-elective)' },
};

/**
 * Render the full term grid
 * @param {object[][]} terms - Array of term arrays from settle()
 * @param {object} config - { maxCreditsPerTerm, termType, onSelectionChange, onDrop }
 * @param {HTMLElement} container - The #term-grid element
 */
export function renderTermGrid(terms, config, container) {
  container.innerHTML = '';
  const { maxCreditsPerTerm = 18, termType = 'semester' } = config;
  const termLabel = getTermLabel(termType);

  for (let t = 0; t < terms.length; t++) {
    const col = document.createElement('div');
    col.className = 'term-column';
    col.dataset.term = t;

    const totalCredits = terms[t].reduce((sum, s) => sum + s.credits, 0);
    const overLimit = totalCredits > maxCreditsPerTerm;

    col.innerHTML = `
      <div class="term-header">
        <span>${termLabel} ${t + 1}</span>
        <span class="term-header__credits ${overLimit ? 'over-limit' : ''}">${totalCredits} cr</span>
      </div>
      <div class="term-courses" data-term="${t}"></div>
    `;

    const coursesDiv = col.querySelector('.term-courses');

    for (const slot of terms[t]) {
      const card = renderCourseCard(slot, config);
      coursesDiv.appendChild(card);
    }

    container.appendChild(col);
  }

  // Initialize drag-and-drop
  initDrag(container, config.onDrop);

  // Render legend
  renderLegend(terms);
}

/**
 * Get the state key for a slot's grade
 */
function gradeKey(slot) {
  return slot.rule === 'open-elective'
    ? `${slot.categoryId}_elective_${slot.electiveIndex}`
    : slot.code;
}

/**
 * Create a grade select element for a course card
 */
function createGradeSelect(slot, config) {
  const key = gradeKey(slot);
  const currentGrade = (config.userGrades || {})[key] || '';

  const wrapper = document.createElement('div');
  wrapper.className = 'course-card__grade';

  const sel = document.createElement('select');
  sel.className = 'grade-select';
  sel.dataset.gradeKey = key;
  for (const g of GRADES) {
    const opt = document.createElement('option');
    opt.value = g;
    opt.textContent = g || '—';
    if (g === currentGrade) opt.selected = true;
    sel.appendChild(opt);
  }
  sel.addEventListener('change', () => {
    if (config.onGradeChange) config.onGradeChange(key, sel.value);
  });

  wrapper.appendChild(sel);
  return wrapper;
}

/**
 * Render a single course card
 */
function renderCourseCard(slot, config) {
  const card = document.createElement('div');
  card.className = 'course-card';
  card.dataset.code = slot.code;
  card.dataset.categoryType = slot.categoryType;

  if (slot.rule === 'open-elective') {
    card.classList.add('course-card--elective');
    card.draggable = true;
    card.innerHTML = `
      <div class="course-card__header">
        <span class="course-card__code">${slot.categoryLabel} ${(slot.electiveIndex || 0) + 1}</span>
        <span class="course-card__credits">${slot.credits} cr</span>
      </div>
      <input type="text" placeholder="Enter course..." value="${slot.title === 'Open Elective' ? '' : slot.code}" data-elective-key="${slot.categoryId}_elective_${slot.electiveIndex}">
      <span class="print-value" style="display:none">${slot.code}</span>
    `;
    card.appendChild(createGradeSelect(slot, config));
    return card;
  }

  if (slot.rule === 'pick') {
    card.classList.add('course-card--pick');
    card.draggable = true;
    const options = (slot.pickOptions || []).map(code => {
      const selected = code === slot.code ? 'selected' : '';
      return `<option value="${code}" ${selected}>${code}</option>`;
    }).join('');

    card.innerHTML = `
      <div class="course-card__header">
        <span class="course-card__code">${slot.categoryLabel}</span>
        <span class="course-card__credits">${slot.credits} cr</span>
      </div>
      <select data-pick-key="${slot.categoryId}_${slot.pickIndex}">${options}</select>
      <div class="course-card__title">${slot.title}</div>
      <span class="print-value" style="display:none">${slot.code} — ${slot.title}</span>
    `;

    // Wire change handler
    const select = card.querySelector('select[data-pick-key]');
    select.addEventListener('change', () => {
      if (config.onSelectionChange) {
        config.onSelectionChange(select.dataset.pickKey, select.value);
      }
    });

    card.appendChild(createGradeSelect(slot, config));
    return card;
  }

  if (slot.rule === 'choose_track' && slot.sequenceIndex === 0) {
    // First course in track — show track selector
    card.draggable = true;
    const trackOpts = (slot.trackOptions || []).map(t => {
      const sel = t === slot.trackName ? 'selected' : '';
      return `<option value="${t}" ${sel}>${t.charAt(0).toUpperCase() + t.slice(1)}</option>`;
    }).join('');

    card.innerHTML = `
      <div class="course-card__header">
        <span class="course-card__code">${slot.code}</span>
        <span class="course-card__credits">${slot.credits} cr</span>
      </div>
      <div class="course-card__title">${slot.title}</div>
      <div style="margin-top:0.25rem;">
        <label style="font-size:0.7rem;color:var(--color-text-muted)">Track:</label>
        <select data-track-key="${slot.categoryId}" style="font-size:0.78rem;padding:0.1rem;">${trackOpts}</select>
      </div>
      <span class="print-value" style="display:none">${slot.code} — ${slot.title}</span>
    `;

    const select = card.querySelector('select[data-track-key]');
    select.addEventListener('change', () => {
      if (config.onSelectionChange) {
        config.onSelectionChange(slot.categoryId, select.value);
      }
    });

    card.appendChild(createGradeSelect(slot, config));
    return card;
  }

  // Default: fixed, sequence, prereq-order, or subsequent choose_track courses
  card.draggable = true;
  card.innerHTML = `
    <div class="course-card__header">
      <span class="course-card__code">${slot.code}</span>
      <span class="course-card__credits">${slot.credits} cr</span>
    </div>
    <div class="course-card__title">${slot.title}</div>
  `;

  card.appendChild(createGradeSelect(slot, config));
  return card;
}

/**
 * Render category legend
 */
function renderLegend(terms) {
  const footer = document.querySelector('.legend');
  const legendItems = document.getElementById('legend-items');
  if (!footer || !legendItems) return;

  // Find which category types are actually used
  const usedTypes = new Set();
  for (const term of terms) {
    for (const slot of term) {
      usedTypes.add(slot.categoryType);
    }
  }

  legendItems.innerHTML = '';
  for (const [type, info] of Object.entries(CATEGORY_COLORS)) {
    if (!usedTypes.has(type)) continue;
    const item = document.createElement('div');
    item.className = 'legend__item';
    item.innerHTML = `<div class="legend__swatch" style="background:${info.color}"></div><span>${info.label}</span>`;
    legendItems.appendChild(item);
  }

  footer.hidden = false;
}

function getTermLabel(termType) {
  switch (termType) {
    case 'trimester': return 'Trimester';
    case 'bimester': return 'Bimester';
    default: return 'Semester';
  }
}

/**
 * Update credit display for a single term column
 */
export function updateTermCredits(termEl, maxCreditsPerTerm) {
  const courses = termEl.querySelector('.term-courses');
  if (!courses) return;
  const cards = courses.querySelectorAll('.course-card');
  let total = 0;
  for (const card of cards) {
    const credEl = card.querySelector('.course-card__credits');
    if (credEl) {
      total += parseInt(credEl.textContent) || 3;
    }
  }
  const badge = termEl.querySelector('.term-header__credits');
  if (badge) {
    badge.textContent = `${total} cr`;
    badge.classList.toggle('over-limit', total > maxCreditsPerTerm);
  }
}
