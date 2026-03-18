/**
 * print.js — Print preparation: builds a temporary table-based layout
 * matching the institutional PDF template format.
 */

/**
 * Prepare and trigger print.
 * Builds a temporary print-specific DOM with paired semester tables,
 * appends it, prints, then removes it.
 * @param {object} state - App state with termSlots, degreeConfig, userGrades, coursesMap
 */
export function preparePrint(state) {
  // Read current values from live DOM before building print layout
  const electiveValues = {};
  document.querySelectorAll('.course-card--elective input').forEach(input => {
    electiveValues[input.dataset.electiveKey] = input.value;
  });

  const pickValues = {};
  document.querySelectorAll('select[data-pick-key]').forEach(sel => {
    pickValues[sel.dataset.pickKey] = sel.value;
  });

  const gradeValues = {};
  document.querySelectorAll('.grade-select').forEach(sel => {
    gradeValues[sel.dataset.gradeKey] = sel.value;
  });

  // Build and insert the print layout
  const printContainer = buildPrintLayout(state, electiveValues, pickValues, gradeValues);
  document.body.appendChild(printContainer);

  window.print();

  // Clean up after print
  printContainer.remove();
}

/**
 * Build the full print layout DOM
 */
function buildPrintLayout(state, electiveValues, pickValues, gradeValues) {
  const container = document.createElement('div');
  container.className = 'print-layout';

  const deg = state.degreeConfig;
  const studentName = document.getElementById('print-student-name')?.value || '';
  const studentNumber = document.getElementById('print-student-number')?.value || '';

  // Header
  const header = document.createElement('div');
  header.className = 'print-layout__header';
  header.innerHTML = `
    <div class="print-layout__degree-name">${escapeHtml(deg.label)}</div>
    <div class="print-layout__student-row">
      <span>Name: <span class="print-layout__field">${escapeHtml(studentName) || '________________________________________'}</span></span>
      <span>Student Number: <span class="print-layout__field">${escapeHtml(studentNumber) || '________________________'}</span></span>
    </div>
  `;
  container.appendChild(header);

  const terms = state.termSlots;
  const termLabel = deg.term_type === 'trimester' ? 'Trimester' :
                    deg.term_type === 'bimester' ? 'Bimester' : 'Semester';

  // Pair terms into year rows (2 semesters side-by-side)
  for (let i = 0; i < terms.length; i += 2) {
    const yearNum = Math.floor(i / 2) + 1;
    const yearNames = ['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth'];
    const yearTitle = (yearNames[yearNum - 1] || `Year ${yearNum}`) + ' Year';

    const yearSection = document.createElement('div');
    yearSection.className = 'print-layout__year';

    const yearHeader = document.createElement('div');
    yearHeader.className = 'print-layout__year-title';
    yearHeader.textContent = yearTitle.toUpperCase();
    yearSection.appendChild(yearHeader);

    const yearRow = document.createElement('div');
    yearRow.className = 'print-layout__year-row';

    // Left semester
    yearRow.appendChild(buildTermTable(
      terms[i], i, termLabel, state, electiveValues, pickValues, gradeValues
    ));

    // Right semester (if exists)
    if (i + 1 < terms.length) {
      yearRow.appendChild(buildTermTable(
        terms[i + 1], i + 1, termLabel, state, electiveValues, pickValues, gradeValues
      ));
    }

    yearSection.appendChild(yearRow);
    container.appendChild(yearSection);
  }

  return container;
}

/**
 * Build a single semester table
 */
function buildTermTable(termSlots, termIndex, termLabel, state, electiveValues, pickValues, gradeValues) {
  const table = document.createElement('table');
  table.className = 'print-term-table';

  const totalCredits = termSlots.reduce((sum, s) => sum + s.credits, 0);
  const semesterNames = ['First', 'Second'];
  const semesterLabel = `${semesterNames[termIndex % 2] || ''} ${termLabel}`.toUpperCase();

  // Build thead
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

  // Build tbody
  const tbody = document.createElement('tbody');
  for (const slot of termSlots) {
    const row = document.createElement('tr');
    const displayInfo = getDisplayInfo(slot, electiveValues, pickValues);
    const prereqs = (slot.prereqs || []).join(', ');
    const gradeKey = slot.rule === 'open-elective'
      ? `${slot.categoryId}_elective_${slot.electiveIndex}`
      : slot.code;
    const grade = gradeValues[gradeKey] || state.userGrades[gradeKey] || '';

    row.innerHTML = `
      <td class="print-term-table__code">${escapeHtml(displayInfo.code)}</td>
      <td class="print-term-table__title">${escapeHtml(displayInfo.title)}</td>
      <td class="print-term-table__credits">${slot.credits}</td>
      <td class="print-term-table__prereqs">${escapeHtml(prereqs)}</td>
      <td class="print-term-table__grade">${escapeHtml(grade)}</td>
    `;
    tbody.appendChild(row);
  }
  table.appendChild(tbody);

  // Build tfoot with totals
  const tfoot = document.createElement('tfoot');
  const totalRow = document.createElement('tr');
  totalRow.innerHTML = `
    <td colspan="2" class="print-term-table__total-label">Total</td>
    <td class="print-term-table__credits print-term-table__total-value">${totalCredits}</td>
    <td colspan="2"></td>
  `;
  tfoot.appendChild(totalRow);
  table.appendChild(tfoot);

  return table;
}

/**
 * Get display code and title for a slot, reading current UI state
 */
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
 * Basic HTML escaping
 */
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
