/**
 * drag.js — HTML5 Drag and Drop for course cards between terms
 */

import { updateTermCredits } from './renderer.js';

let draggedCard = null;
let sourceTerm = null;

/**
 * Initialize drag-and-drop on the term grid
 * @param {HTMLElement} container - The #term-grid element
 * @param {Function} onDrop - Callback: (courseCode, fromTerm, toTerm) => void
 */
export function initDrag(container, onDrop) {
  // Delegate events on the container
  container.addEventListener('dragstart', handleDragStart);
  container.addEventListener('dragend', handleDragEnd);
  container.addEventListener('dragover', handleDragOver);
  container.addEventListener('dragleave', handleDragLeave);
  container.addEventListener('drop', (e) => handleDrop(e, onDrop));
}

function handleDragStart(e) {
  const card = e.target.closest('.course-card');
  if (!card) return;
  draggedCard = card;
  sourceTerm = card.closest('.term-column');
  card.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', card.dataset.code);
}

function handleDragEnd(e) {
  if (draggedCard) {
    draggedCard.classList.remove('dragging');
  }
  // Remove all drag-over highlights
  document.querySelectorAll('.term-column.drag-over').forEach(el => {
    el.classList.remove('drag-over');
  });
  draggedCard = null;
  sourceTerm = null;
}

function handleDragOver(e) {
  const termCol = e.target.closest('.term-column');
  if (!termCol || !draggedCard) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  termCol.classList.add('drag-over');
}

function handleDragLeave(e) {
  const termCol = e.target.closest('.term-column');
  if (termCol && !termCol.contains(e.relatedTarget)) {
    termCol.classList.remove('drag-over');
  }
}

function handleDrop(e, onDrop) {
  e.preventDefault();
  const termCol = e.target.closest('.term-column');
  if (!termCol || !draggedCard) return;

  termCol.classList.remove('drag-over');

  // Don't drop on same term
  if (termCol === sourceTerm) return;

  const courseCode = draggedCard.dataset.code;
  const fromTerm = parseInt(sourceTerm.dataset.term, 10);
  const toTerm = parseInt(termCol.dataset.term, 10);

  // Move the card DOM element
  const targetCourses = termCol.querySelector('.term-courses');
  targetCourses.appendChild(draggedCard);

  // Update credit badges for both terms
  const maxCredits = parseInt(document.body.dataset.maxCredits || '18', 10);
  updateTermCredits(sourceTerm, maxCredits);
  updateTermCredits(termCol, maxCredits);

  // Notify app of the move
  if (onDrop) {
    onDrop(courseCode, fromTerm, toTerm);
  }
}
