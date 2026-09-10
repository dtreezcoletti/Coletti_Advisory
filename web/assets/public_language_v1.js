/* Public-facing vocabulary normalization and universal professional-boundary presentation.
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

function currentPublicRoute() {
  const raw = (location.hash || '#/home').replace(/^#\/?/, '');
  return (raw.split('/')[0] || 'home').toLowerCase();
}

function publicRouteActive() {
  return PUBLIC_ROUTES.has(currentPublicRoute());
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

function splitServicesScopeNotice() {
  if (currentPublicRoute() !== 'services') return;
  const notices = [...document.querySelectorAll('#main .notice.notice-info')];
  const combined = 'Engagement scope is confirmed before substantive work begins. A reconstruction engagement does not authorize Coletti & Co. to act as your attorney, accountant, auditor, investigator, fiduciary, or other licensed professional.';
  for (const notice of notices) {
    const text = (notice.textContent || '').trim().replace(/\s+/g, ' ');
    if (text === combined || text.includes('Engagement scope is confirmed before substantive work begins. A reconstruction engagement does not authorize Coletti & Co.')) {
      notice.textContent = 'Engagement scope is confirmed before substantive work begins.';
      notice.setAttribute('data-page-scope-notice', 'true');
    }
  }
}

function ensureProfessionalBoundary() {
  const footer = document.getElementById('site-footer');
  if (!footer) return;

  let boundary = document.getElementById('professional-boundary-band');
  if (!publicRouteActive()) {
    boundary?.remove();
    return;
  }

  if (!boundary) {
    boundary = document.createElement('section');
    boundary.id = 'professional-boundary-band';
    boundary.className = 'professional-boundary-band';
    boundary.setAttribute('aria-label', 'Professional services boundary');
    boundary.innerHTML = `
      <div class="professional-boundary-inner">
        <div class="professional-boundary-kicker">Professional Boundary</div>
        <div class="professional-boundary-copy">
          <h2>Records reconstruction is not substituted professional judgment.</h2>
          <p>A reconstruction engagement does not authorize Coletti &amp; Co. to act as your attorney, accountant, auditor, investigator, fiduciary, or other licensed professional. Where licensed or regulated professional judgment is required, Coletti &amp; Co. preserves the record and prepares the work for handoff to the appropriate qualified professional.</p>
        </div>
        <a class="professional-boundary-link" href="#/disclaimer">Read the full boundary →</a>
      </div>`;
    footer.parentNode.insertBefore(boundary, footer);
  }
}

function applyPublicVocabulary() {
  if (!publicRouteActive()) {
    ensureProfessionalBoundary();
    return;
  }
  splitServicesScopeNotice();
  ensureProfessionalBoundary();
  normalizeNode(document.getElementById('site-header'));
  normalizeNode(document.getElementById('main'));
  normalizeNode(document.getElementById('professional-boundary-band'));
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
