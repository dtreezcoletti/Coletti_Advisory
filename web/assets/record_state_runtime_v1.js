/* Canonical Record State presentation/runtime compatibility layer.
 *
 * The database and Core still retain a few legacy `evidence_state` field names for
 * non-breaking compatibility. This layer makes the browser contract canonical:
 * Record / Record State, including Identified Pattern.
 */

const RECORD_STATES = Object.freeze([
  'Documented Fact',
  'Reconciliation Result',
  'Inconsistency',
  'Missing Documentation',
  'Process Deviation',
  'Unresolved Question',
  'Client Assertion',
  'Third-Party Conclusion',
  'Referral Required',
  'Identified Pattern'
]);

const IDENTIFIED_PATTERN_DEFINITION =
  'A recurring, clustered, repeated, correlated, sequential, or otherwise materially consistent relationship observed across two or more records or events. It describes the relationship shown by the records and does not by itself establish motive, intent, illegality, liability, causation, or protected professional effect.';

const PROTECTED_PROFESSION_RULE =
  'ColettiOS can determine the condition of the records; it cannot independently determine the protected professional effect of that condition.';

// Expose a read-only browser contract for other UI modules without changing any
// authorization or database semantics.
Object.defineProperty(window, 'COLETTI_RECORD_STATES', {
  value: RECORD_STATES,
  writable: false,
  configurable: false
});
Object.defineProperty(window, 'COLETTI_PROTECTED_PROFESSION_RULE', {
  value: PROTECTED_PROFESSION_RULE,
  writable: false,
  configurable: false
});

function isRecordStateSelect(select) {
  const values = [...select.options].map(option => option.value || option.textContent || '');
  return values.includes('Documented Fact') && values.includes('Referral Required');
}

function completeRecordStateSelect(select) {
  if (!isRecordStateSelect(select)) return;
  const values = new Set([...select.options].map(option => option.value || option.textContent || ''));
  for (const state of RECORD_STATES) {
    if (values.has(state)) continue;
    const option = document.createElement('option');
    option.value = state;
    option.textContent = state;
    if (state === 'Identified Pattern') option.title = IDENTIFIED_PATTERN_DEFINITION;
    select.appendChild(option);
  }
  select.dataset.recordStateContract = 'v1';
}

const INTERNAL_LABEL_REPLACEMENTS = [
  [/Evidence State/g, 'Record State'],
  [/Evidence state/g, 'Record State'],
  [/evidence state/g, 'Record State'],
  [/Evidence Work Items/g, 'Record State Work Items'],
  [/Evidence work items/g, 'Record State work items'],
  [/Evidence\/provenance/g, 'Records/provenance'],
  [/Evidence Workspace/g, 'Records Workspace']
];

function canonicalizeTextNode(node) {
  let text = node.nodeValue || '';
  let next = text;
  for (const [pattern, replacement] of INTERNAL_LABEL_REPLACEMENTS) {
    next = next.replace(pattern, replacement);
  }
  if (next !== text) node.nodeValue = next;
}

function applyRecordStateContract(root = document) {
  for (const select of root.querySelectorAll?.('select') || []) completeRecordStateSelect(select);

  const scope = root === document ? document.body : root;
  if (scope) {
    const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) canonicalizeTextNode(node);
  }

  for (const badge of root.querySelectorAll?.('.badge') || []) {
    if ((badge.textContent || '').trim() === 'Identified Pattern') {
      badge.title = IDENTIFIED_PATTERN_DEFINITION;
    }
  }
}

let scheduled = false;
function scheduleApply() {
  if (scheduled) return;
  scheduled = true;
  queueMicrotask(() => {
    scheduled = false;
    applyRecordStateContract();
  });
}

window.addEventListener('DOMContentLoaded', scheduleApply);
window.addEventListener('hashchange', scheduleApply);
new MutationObserver(scheduleApply).observe(document.documentElement, {
  subtree: true,
  childList: true,
  characterData: true
});

scheduleApply();
