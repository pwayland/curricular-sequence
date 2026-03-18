/**
 * app.js — Main entry point: state management, dropdown wiring, event handling
 */

import { loadCatalogYears, loadCourses, loadGenEdTemplate, loadDegree, mergeGenEd, resolveSlots, resolveDegreeAlias } from './yaml-loader.js';
import { settle, validatePlacements } from './settling.js';
import { renderTermGrid } from './renderer.js';
import { preparePrint } from './print.js';

// ── State ────────────────────────────────────────────
const state = {
  catalogYears: [],
  selectedYear: null,
  selectedDegreeId: null,
  degreeConfig: null,
  genEd: null,
  coursesMap: null,
  termSlots: [],
  userPins: {},       // code → termIndex (from drag)
  userSelections: {}, // categoryId → value (from pick/track dropdowns)
  userGrades: {},     // gradeKey → grade string (e.g. "A", "IP")
};

// ── DOM refs ─────────────────────────────────────────
const elYear = document.getElementById('catalog-year');
const elDegree = document.getElementById('degree');
const elBtnResettle = document.getElementById('btn-resettle');
const elBtnReset = document.getElementById('btn-reset');
const elBtnPrint = document.getElementById('btn-print');
const elGrid = document.getElementById('term-grid');
const elDegreeInfo = document.getElementById('degree-info');
const elDegreeLabel = document.getElementById('degree-label');
const elDegreeCredits = document.getElementById('degree-credits');
const elDegreeTerms = document.getElementById('degree-terms');

// ── Init ─────────────────────────────────────────────
async function init() {
  try {
    state.catalogYears = await loadCatalogYears();
    populateYearDropdown();
    wireEvents();
    showEmptyState('Select a catalog year and degree to begin.');
  } catch (err) {
    showEmptyState(`Error loading data: ${err.message}. Make sure to serve this via a local HTTP server.`);
  }
}

function populateYearDropdown() {
  elYear.innerHTML = '<option value="">Select year...</option>';
  for (const year of state.catalogYears) {
    const opt = document.createElement('option');
    opt.value = year.id;
    opt.textContent = year.label;
    elYear.appendChild(opt);
  }
}

function populateDegreeDropdown(year) {
  elDegree.innerHTML = '<option value="">Select degree...</option>';
  if (!year) {
    elDegree.disabled = true;
    return;
  }
  for (const deg of year.degrees) {
    const opt = document.createElement('option');
    opt.value = deg.id;
    opt.textContent = deg.label;
    elDegree.appendChild(opt);
  }
  elDegree.disabled = false;
}

// ── Events ───────────────────────────────────────────
function wireEvents() {
  elYear.addEventListener('change', onYearChange);
  elDegree.addEventListener('change', onDegreeChange);
  elBtnResettle.addEventListener('click', onResettle);
  elBtnReset.addEventListener('click', onReset);
  elBtnPrint.addEventListener('click', () => preparePrint(state));
}

function onYearChange() {
  const yearId = elYear.value;
  state.selectedYear = state.catalogYears.find(y => y.id === yearId) || null;
  state.selectedDegreeId = null;
  state.userPins = {};
  state.userSelections = {};
  state.userGrades = {};
  populateDegreeDropdown(state.selectedYear);
  setButtonsEnabled(false);
  hideDegreeInfo();
  showEmptyState('Select a degree.');
}

async function onDegreeChange() {
  const degreeId = elDegree.value;
  if (!degreeId || !state.selectedYear) {
    setButtonsEnabled(false);
    showEmptyState('Select a degree.');
    return;
  }

  state.selectedDegreeId = degreeId;
  state.userPins = {};
  state.userSelections = {};
  state.userGrades = {};

  const degreeEntry = state.selectedYear.degrees.find(d => d.id === degreeId);
  if (!degreeEntry) return;

  try {
    showEmptyState('Loading...');

    // Resolve alias if this degree points to another year's version
    const { file: degreeFile, aliasOf, aliasYear } = resolveDegreeAlias(degreeEntry, state.catalogYears);

    // If aliased, use the target year's courses file; otherwise use current year's
    const coursesFile = aliasYear ? aliasYear.courses_file : state.selectedYear.courses_file;

    // Load degree, courses, and gen-ed template in parallel
    const [degreeConfig, coursesMap] = await Promise.all([
      loadDegree(degreeFile),
      loadCourses(coursesFile),
    ]);

    state.degreeConfig = degreeConfig;
    state.degreeConfig._aliasOf = aliasOf;
    state.coursesMap = coursesMap;

    // Load and merge gen-ed
    if (degreeConfig.gen_ed && degreeConfig.gen_ed.template) {
      const template = await loadGenEdTemplate(degreeConfig.gen_ed.template);
      state.genEd = mergeGenEd(template, degreeConfig.gen_ed.overrides);
    } else {
      state.genEd = { categories: [] };
    }

    showDegreeInfo();
    runSettle();
    setButtonsEnabled(true);
  } catch (err) {
    showEmptyState(`Error loading degree: ${err.message}`);
  }
}

// ── Settle & Render ──────────────────────────────────
function runSettle() {
  const deg = state.degreeConfig;
  const slots = resolveSlots(deg, state.genEd, state.coursesMap, state.userSelections);

  state.termSlots = settle(slots, {
    maxCreditsPerTerm: deg.max_credits_per_term || 18,
    termsCount: deg.terms_count || 8,
    termPins: deg.term_pins || {},
    userPins: state.userPins,
  });

  // Store max credits on body for drag.js
  document.body.dataset.maxCredits = deg.max_credits_per_term || 18;

  renderTermGrid(state.termSlots, {
    maxCreditsPerTerm: deg.max_credits_per_term || 18,
    termType: deg.term_type || 'semester',
    onSelectionChange: handleSelectionChange,
    onGradeChange: handleGradeChange,
    onDrop: handleDrop,
    userGrades: state.userGrades,
  }, elGrid);

  // Validate and warn
  const violations = validatePlacements(state.termSlots);
  if (violations.length > 0) {
    console.warn('Prerequisite violations:', violations);
  }
}

function handleSelectionChange(key, value) {
  state.userSelections[key] = value;
  runSettle();
}

function handleGradeChange(key, grade) {
  if (grade) {
    state.userGrades[key] = grade;
  } else {
    delete state.userGrades[key];
  }
}

function handleDrop(courseCode, fromTerm, toTerm) {
  state.userPins[courseCode] = toTerm;
}

function onResettle() {
  runSettle();
}

function onReset() {
  state.userPins = {};
  state.userSelections = {};
  state.userGrades = {};
  runSettle();
}

// ── UI Helpers ───────────────────────────────────────
function setButtonsEnabled(enabled) {
  elBtnResettle.disabled = !enabled;
  elBtnReset.disabled = !enabled;
  elBtnPrint.disabled = !enabled;
}

function showEmptyState(message) {
  elGrid.innerHTML = `<div class="empty-state">${message}</div>`;
}

function showDegreeInfo() {
  const deg = state.degreeConfig;
  const termLabel = deg.term_type === 'trimester' ? 'trimesters' :
                    deg.term_type === 'bimester' ? 'bimesters' : 'semesters';
  elDegreeLabel.textContent = deg.label;
  elDegreeCredits.textContent = `${deg.total_credits} credits`;
  elDegreeTerms.textContent = `${deg.terms_count} ${termLabel}`;
  // Show alias indicator if this degree is an alias of another year
  const aliasEl = document.getElementById('degree-alias');
  if (aliasEl) {
    if (deg._aliasOf) {
      const [yearId] = deg._aliasOf.split('/');
      const targetYear = state.catalogYears.find(y => y.id === yearId);
      aliasEl.textContent = `Same as ${targetYear ? targetYear.label : yearId}`;
      aliasEl.hidden = false;
    } else {
      aliasEl.hidden = true;
    }
  }
  elDegreeInfo.hidden = false;
  document.getElementById('print-header').hidden = false;
}

function hideDegreeInfo() {
  elDegreeInfo.hidden = true;
  document.getElementById('print-header').hidden = true;
}

// ── Boot ─────────────────────────────────────────────
init();
