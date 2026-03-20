/**
 * print.js — Print preparation: builds a paginated, multi-page layout
 * matching the institutional curricular sequence form format.
 *
 * Page 1:  Institution header, info columns (name/student-no, requirements,
 *          language table), first 2 terms, footer.
 * Pages 2+: Up to 4 terms (2 years) each, footer with degree info.
 */

// ── Defaults (overridable per degree via `print:` section in YAML) ──────────

const PRINT_DEFAULTS = {
  institution: 'Inter American University of Puerto Rico',
  campus: 'Metropolitan Campus',
  department: 'Business and Technology',
  subcategory: 'Undergraduate',
  degree_code: '',
  campus_website: 'metro.inter.edu',
  campus_phone: '(787) 250-1912',
  department_logo: '',
  institution_logo: '',
};

const LANGUAGE_TABLES = {
  bachelor: {
    header:
      'In the English curriculum the student will take one of the following sequences, according to the College Board score:',
    rows: [
      ['Level 1 Elementary (440 or less)', 'GEEN 1101, GEEN 1102, GEEN 1103'],
      ['Level 2 Intermediate (441 to 580)', 'GEEN 1201, GEEN 1202, GEEN 1203'],
      ['Level 3 Advanced (581 or more)', 'GEEN 2311, GEEN 2312, GEEN 2313'],
    ],
    footer:
      'Three (3) consecutive Spanish courses are required. Students whose native language is not Spanish will be required to take GESP 1021, GESP 1022 and GESP 2023.',
  },
  associate: {
    header:
      'In the English curriculum the student will take one of the following sequences, according to the College Board score:',
    rows: [
      ['Level 1 Elementary (440 or less)', 'GEEN 1101, GEEN 1102'],
      ['Level 2 Intermediate (441 to 580)', 'GEEN 1201, GEEN 1202'],
      ['Level 3 Advanced (581 or more)', 'GEEN 2311, GEEN 2312'],
    ],
    footer:
      'Two (2) consecutive Spanish courses are required. Students whose native language is not Spanish will be required to take GESP 1021 and GESP 1022.',
  },
};

// ── Public API ──────────────────────────────────────────────────────────────

/**
 * Prepare and trigger print.
 * @param {object} state - App state
 */
export function preparePrint(state) {
  // Snapshot live DOM values before building print layout
  const ctx = {
    electiveValues: {},
    pickValues: {},
    gradeValues: {},
    userGrades: state.userGrades || {},
  };

  document.querySelectorAll('.course-card--elective input').forEach(input => {
    ctx.electiveValues[input.dataset.electiveKey] = input.value;
  });
  document.querySelectorAll('select[data-pick-key]').forEach(sel => {
    ctx.pickValues[sel.dataset.pickKey] = sel.value;
  });
  document.querySelectorAll('.grade-select').forEach(sel => {
    ctx.gradeValues[sel.dataset.gradeKey] = sel.value;
  });

  const printContainer = buildPrintLayout(state, ctx);
  document.body.appendChild(printContainer);

  const cleanup = () => {
    printContainer.remove();
    window.removeEventListener('afterprint', cleanup);
  };
  window.addEventListener('afterprint', cleanup);

  window.print();
}

// ── Layout builder ──────────────────────────────────────────────────────────

function buildPrintLayout(state, ctx) {
  const container = document.createElement('div');
  container.className = 'print-layout';

  const deg = state.degreeConfig;
  const cfg = { ...PRINT_DEFAULTS, ...(deg.print || {}) };
  const studentName = document.getElementById('print-student-name')?.value || '';
  const studentNumber = document.getElementById('print-student-number')?.value || '';
  const yearLabel = state.selectedYear?.label || '';
  const terms = state.termSlots;
  const termLabel =
    deg.term_type === 'trimester'
      ? 'Trimester'
      : deg.term_type === 'bimester'
        ? 'Bimester'
        : 'Semester';
  const degreeDisplay = cfg.degree_code
    ? `${deg.label} (${cfg.degree_code})`
    : deg.label;

  // Pagination: page 1 = 2 terms, subsequent pages = 4 terms each
  const TERMS_PAGE1 = 2;
  const TERMS_REST = 4;
  const remaining = Math.max(0, terms.length - TERMS_PAGE1);
  const totalPages = 1 + Math.ceil(remaining / TERMS_REST);

  // ── Page 1 ──────────────────────────────────────────────
  const p1 = makePage(true);

  p1.body.appendChild(
    buildInstitutionHeader(cfg, degreeDisplay),
  );
  p1.body.appendChild(
    buildInfoSection(cfg, yearLabel, studentName, studentNumber, state),
  );

  // First year (terms 0–1)
  const year1 = buildYearSection(terms, 0, termLabel, ctx);
  if (year1) p1.body.appendChild(year1);

  p1.footer.innerHTML = `<span>Page 1 of ${totalPages}</span>`;
  container.appendChild(p1.el);

  // ── Pages 2+ ───────────────────────────────────────────
  let termIdx = TERMS_PAGE1;
  let pageNum = 2;

  while (termIdx < terms.length) {
    const page = makePage(false);

    // Up to 2 year-sections (4 terms) per page
    for (let y = 0; y < 2 && termIdx < terms.length; y++) {
      const yearSection = buildYearSection(terms, termIdx, termLabel, ctx);
      if (yearSection) page.body.appendChild(yearSection);
      termIdx += 2;
    }

    // End-of-degree notes on the last page
    if (termIdx >= terms.length) {
      const endNotes = buildEndNotes(deg);
      if (endNotes) page.body.appendChild(endNotes);
    }

    page.footer.innerHTML = `
      <div>${escapeHtml(degreeDisplay)}</div>
      <div>Page ${pageNum} of ${totalPages}</div>
      <div>${escapeHtml(yearLabel)}</div>
    `;
    container.appendChild(page.el);
    pageNum++;
  }

  return container;
}

// ── Page wrapper ────────────────────────────────────────────────────────────

function makePage(isFirst) {
  const el = document.createElement('div');
  el.className = 'print-page' + (isFirst ? ' print-page--first' : '');

  const body = document.createElement('div');
  body.className = 'print-page__body';
  el.appendChild(body);

  const footer = document.createElement('div');
  footer.className = 'print-page__footer';
  el.appendChild(footer);

  return { el, body, footer };
}

// ── Institution header (top of page 1) ──────────────────────────────────────

function buildInstitutionHeader(cfg, degreeDisplay) {
  const header = document.createElement('div');
  header.className = 'print-page__header';

  // Left: logo or department text
  const logoArea = document.createElement('div');
  logoArea.className = 'print-page__logo-area';

  if (cfg.department_logo) {
    logoArea.appendChild(makeImg(cfg.department_logo, cfg.department));
  } else if (cfg.institution_logo) {
    logoArea.appendChild(makeImg(cfg.institution_logo, cfg.institution));
  } else {
    // Text fallback — wrap department name at ≤40 chars
    for (const line of wrapText(cfg.department, 40)) {
      const d = document.createElement('div');
      d.textContent = line;
      logoArea.appendChild(d);
    }
  }
  header.appendChild(logoArea);

  // Center: institutional text
  const text = document.createElement('div');
  text.className = 'print-page__institution-text';
  text.innerHTML = `
    <div class="print-page__inst-name">${escapeHtml(cfg.institution)}</div>
    <div>${escapeHtml(cfg.campus)}</div>
    <div>${escapeHtml(cfg.department)}</div>
    <div>${escapeHtml(cfg.subcategory)}</div>
    <div class="print-page__degree-title">${escapeHtml(degreeDisplay)}</div>
  `;
  header.appendChild(text);

  return header;
}

function makeImg(src, alt) {
  const img = document.createElement('img');
  img.src = src;
  img.alt = alt;
  img.className = 'print-page__logo';
  return img;
}

// ── Info section (two columns, page 1) ──────────────────────────────────────

function buildInfoSection(cfg, yearLabel, studentName, studentNumber, state) {
  const section = document.createElement('div');
  section.className = 'print-page__info-section';

  // ── Left column ──
  const left = document.createElement('div');
  left.className = 'print-page__info-col';
  left.innerHTML = `
    <div class="print-page__info-line">
      ${escapeHtml(cfg.campus_website)} General Catalog (${escapeHtml(yearLabel)})
    </div>
    <div class="print-page__info-field">
      Name: <span class="print-page__field-line">${escapeHtml(studentName)}</span>
    </div>
  `;
  // Requirements table — gen-ed as single line + degree categories + total
  const genEdCredits = state.genEd?.total_credits || 0;
  const reqRows = [
    { label: 'General Education', credits: genEdCredits },
    ...(state.degreeConfig.categories || []).map(c => ({
      label: c.label,
      credits: c.credits || 0,
    })),
  ];
  left.appendChild(
    buildRequirementsTable(
      reqRows,
      'Requirements',
      { showTotal: true, totalCredits: state.degreeConfig.total_credits },
    ),
  );
  section.appendChild(left);

  // ── Right column ──
  const right = document.createElement('div');
  right.className = 'print-page__info-col';
  right.innerHTML = `
    <div class="print-page__info-line">
      <strong>Tel.</strong> ${escapeHtml(cfg.campus_phone)}
    </div>
    <div class="print-page__info-field">
      Student No.: <span class="print-page__field-line">${escapeHtml(studentNumber)}</span>
    </div>
  `;
  // Language curriculum table
  const langTable = buildLanguageTable(state.degreeConfig);
  if (langTable) right.appendChild(langTable);

  // Notes box (standard text + department notes)
  const notesBox = document.createElement('div');
  notesBox.className = 'print-dept-notes';
  for (const line of STANDARD_NOTES) {
    const p = document.createElement('div');
    p.textContent = line;
    notesBox.appendChild(p);
  }
  const deptNotes = cfg.department_notes;
  if (deptNotes) {
    const lines = Array.isArray(deptNotes) ? deptNotes : [deptNotes];
    for (const line of lines) {
      const p = document.createElement('div');
      p.textContent = line;
      notesBox.appendChild(p);
    }
  }
  right.appendChild(notesBox);

  section.appendChild(right);
  return section;
}

const STANDARD_NOTES = [
  'Students must meet all the requirements in the General Catalogue (https://inter.smartcatalogiq.com/).',
  'The Registrar\u2019s Office will officially evaluate after a student has paid the graduation fee.',
];

// ── End-of-degree notes (last page, after final terms) ──────────────────────

function buildEndNotes(deg) {
  const notes = deg.print?.end_notes;
  if (!notes) return null;

  const box = document.createElement('div');
  box.className = 'print-end-notes';

  const lines = Array.isArray(notes) ? notes : [notes];
  for (const line of lines) {
    const p = document.createElement('div');
    p.textContent = line;
    box.appendChild(p);
  }

  return box;
}

// ── Requirements summary table ──────────────────────────────────────────────

function buildRequirementsTable(categories, title, opts = {}) {
  const table = document.createElement('table');
  table.className = 'print-req-table';

  const thead = document.createElement('thead');
  thead.innerHTML = `<tr><th colspan="2">${escapeHtml(title)}</th></tr>`;
  table.appendChild(thead);

  const tbody = document.createElement('tbody');

  for (const cat of categories) {
    const cr = cat.credits || 0;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(cat.label)}</td>
      <td class="print-req-table__credits">${cr}</td>
    `;
    tbody.appendChild(tr);
  }

  // Total row
  if (opts.showTotal && opts.totalCredits != null) {
    const totTr = document.createElement('tr');
    totTr.className = 'print-req-table__total';
    totTr.innerHTML = `
      <td><strong>Total</strong></td>
      <td class="print-req-table__credits"><strong>${opts.totalCredits}</strong></td>
    `;
    tbody.appendChild(totTr);
  }

  table.appendChild(tbody);
  return table;
}

// ── Language curriculum table ───────────────────────────────────────────────

function buildLanguageTable(deg) {
  // Explicitly hidden
  if (deg.print?.language_table === false) return null;

  // Custom override or default by degree type
  const custom = deg.print?.language_table;
  const langData =
    typeof custom === 'object' && custom !== null
      ? custom
      : LANGUAGE_TABLES[deg.degree_type];

  if (!langData) return null;

  const table = document.createElement('table');
  table.className = 'print-lang-table';

  // Header row (spans both columns)
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr><td colspan="2" class="print-lang-table__wide">${escapeHtml(langData.header)}</td></tr>
  `;
  table.appendChild(thead);

  // Data rows
  const tbody = document.createElement('tbody');
  for (const [level, courses] of langData.rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${escapeHtml(level)}</td><td>${escapeHtml(courses)}</td>`;
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);

  // Footer row (spans both columns)
  const tfoot = document.createElement('tfoot');
  tfoot.innerHTML = `
    <tr><td colspan="2" class="print-lang-table__wide">${escapeHtml(langData.footer)}</td></tr>
  `;
  table.appendChild(tfoot);

  return table;
}

// ── Year section (2 side-by-side term tables) ───────────────────────────────

function buildYearSection(terms, startIdx, termLabel, ctx) {
  if (startIdx >= terms.length) return null;

  const yearNum = Math.floor(startIdx / 2) + 1;
  const yearNames = ['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth'];
  const yearTitle =
    (yearNames[yearNum - 1] || `Year ${yearNum}`) + ' Year';

  const section = document.createElement('div');
  section.className = 'print-layout__year';

  const title = document.createElement('div');
  title.className = 'print-layout__year-title';
  title.textContent = yearTitle.toUpperCase();
  section.appendChild(title);

  const row = document.createElement('div');
  row.className = 'print-layout__year-row';

  row.appendChild(buildTermTable(terms[startIdx], startIdx, termLabel, ctx));
  if (startIdx + 1 < terms.length) {
    row.appendChild(
      buildTermTable(terms[startIdx + 1], startIdx + 1, termLabel, ctx),
    );
  }

  section.appendChild(row);
  return section;
}

// ── Single term table ───────────────────────────────────────────────────────

function buildTermTable(termSlots, termIndex, termLabel, ctx) {
  const table = document.createElement('table');
  table.className = 'print-term-table';

  // Colgroup defines column widths for table-layout: fixed
  const colgroup = document.createElement('colgroup');
  colgroup.innerHTML = `
    <col style="width:22%">
    <col style="width:40%">
    <col style="width:7%">
    <col style="width:21%">
    <col style="width:10%">
  `;
  table.appendChild(colgroup);

  const totalCredits = termSlots.reduce((sum, s) => sum + s.credits, 0);
  const semesterNames = ['First', 'Second'];
  const semesterLabel =
    `${semesterNames[termIndex % 2] || ''} ${termLabel}`.toUpperCase();

  // Thead
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr class="print-term-table__semester-header">
      <th colspan="5">${semesterLabel}</th>
    </tr>
    <tr class="print-term-table__col-headers">
      <th>Course</th>
      <th>Course Title</th>
      <th>Credits</th>
      <th>Requirement</th>
      <th>Grade</th>
    </tr>
  `;
  table.appendChild(thead);

  // Tbody
  const tbody = document.createElement('tbody');
  for (const slot of termSlots) {
    const display = getDisplayInfo(slot, ctx.electiveValues, ctx.pickValues);
    const prereqs = (slot.prereqs || []).join(', ');
    const gradeKey =
      slot.rule === 'open-elective'
        ? `${slot.categoryId}_elective_${slot.electiveIndex}`
        : slot.code;
    const grade = ctx.gradeValues[gradeKey] || ctx.userGrades[gradeKey] || '';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="print-term-table__code">${escapeHtml(display.code)}</td>
      <td class="print-term-table__title">${escapeHtml(display.title)}</td>
      <td class="print-term-table__credits">${slot.credits}</td>
      <td class="print-term-table__prereqs">${escapeHtml(prereqs)}</td>
      <td class="print-term-table__grade">${escapeHtml(grade)}</td>
    `;
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);

  // Tfoot
  const tfoot = document.createElement('tfoot');
  tfoot.innerHTML = `
    <tr>
      <td colspan="2" class="print-term-table__total-label">Total</td>
      <td class="print-term-table__credits print-term-table__total-value">${totalCredits}</td>
      <td colspan="2"></td>
    </tr>
  `;
  table.appendChild(tfoot);

  return table;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function getDisplayInfo(slot, electiveValues, pickValues) {
  if (slot.rule === 'open-elective') {
    const key = `${slot.categoryId}_elective_${slot.electiveIndex}`;
    const val = electiveValues[key] || '';
    return {
      code: val || `${slot.categoryLabel} ${(slot.electiveIndex || 0) + 1}`,
      title: val ? '' : 'Open Elective',
    };
  }
  if (slot.rule === 'pick') {
    const key = `${slot.categoryId}_${slot.pickIndex}`;
    const selectedCode = pickValues[key] || slot.code;
    return { code: selectedCode, title: slot.title };
  }
  return { code: slot.code, title: slot.title };
}

/**
 * Word-wrap text into lines of at most `maxLen` characters,
 * breaking only on spaces (never mid-word).
 */
function wrapText(text, maxLen = 40) {
  const words = text.split(' ');
  const lines = [];
  let cur = '';
  for (const w of words) {
    if (cur && cur.length + 1 + w.length > maxLen) {
      lines.push(cur);
      cur = w;
    } else {
      cur = cur ? cur + ' ' + w : w;
    }
  }
  if (cur) lines.push(cur);
  return lines;
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
