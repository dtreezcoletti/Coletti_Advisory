/* Public-facing vocabulary normalization.
   This intentionally changes only presentation text on public routes.
   Internal database/API identifiers and authenticated staff workflow vocabulary remain unchanged. */

const PUBLIC_ROUTES = new Set([
  'home','services','how-it-works','about','referral-partners','pricing','security',
  'faq','contact','disclaimer','privacy','terms','sign-in'
]);

const replacements = [
  [/Evidence Intelligence & Reconstruction/g, 'Records Intelligence & Reconstruction'],
  [/evidence-intelligence and reconstruction/gi, 'records intelligence and reconstruction'],
  [/Independent Evidence Intelligence/g, 'Independent Records Intelligence'],
  [/Evidence states/g, 'Record states'],
  [/evidence states/g, 'record states'],
  [/Evidence state/g, 'Record state'],
  [/evidence state/g, 'record state'],
  [/money-flow evidence/gi, 'money-flow records'],
  [/contrary evidence/gi, 'contrary documentation'],
  [/evidentiary-admissibility/gi, 'admissibility'],
  [/evidentiary admissibility/gi, 'admissibility'],
  [/evidentiary determination/gi, 'admissibility determination'],
  [/\bEvidence\b/g, 'Records'],
  [/\bevidence\b/g, 'record material'],
  [/\bevidentiary\b/gi, 'admissibility-related']
];

function publicRouteActive() {
  const raw = (location.hash || '#/home').replace(/^#\/?/, '');
  const route = (raw.split('/')[0] || 'home').toLowerCase();
  return PUBLIC_ROUTES.has(route);
}

function normalizeText(value) {
  let next = String(value ?? '');
  for (const [pattern, replacement] of replacements) next = next.replace(pattern, replacement);
  return next;
}

function normalizeNode(root) {
  if (!publicRouteActive() || !root) return;

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const next = normalizeText(node.nodeValue);
    if (next !== node.nodeValue) node.nodeValue = next;
  }

  const elements = root.querySelectorAll?.('[aria-label],[title],[placeholder]') || [];
  for (const el of elements) {
    for (const attr of ['aria-label','title','placeholder']) {
      if (!el.hasAttribute(attr)) continue;
      const current = el.getAttribute(attr);
      const next = normalizeText(current);
      if (next !== current) el.setAttribute(attr, next);
    }
  }
}

function applyPublicVocabulary() {
  if (!publicRouteActive()) return;
  normalizeNode(document.getElementById('site-header'));
  normalizeNode(document.getElementById('main'));
  normalizeNode(document.getElementById('site-footer'));
  const description = document.querySelector('meta[name="description"]');
  if (description) description.setAttribute('content', normalizeText(description.getAttribute('content')));
}

let scheduled = false;
function scheduleNormalization() {
  if (scheduled) return;
  scheduled = true;
  queueMicrotask(() => {
    scheduled = false;
    applyPublicVocabulary();
  });
}

window.addEventListener('hashchange', scheduleNormalization);
window.addEventListener('DOMContentLoaded', scheduleNormalization);
new MutationObserver(scheduleNormalization).observe(document.documentElement, {
  subtree: true,
  childList: true,
  characterData: true
});

scheduleNormalization();
