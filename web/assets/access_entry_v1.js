/* Coletti & Co. access-entry layer.
 * Presentation/routing only. Authentication and authorization remain in Supabase.
 */

const SIGN_IN = '/#/sign-in';

function isPublicSignedOutHeader(actions) {
  return actions && /Secure Sign In/i.test(actions.textContent || '');
}

function enhanceHeader() {
  const actions = document.querySelector('.header-actions');
  if (!isPublicSignedOutHeader(actions) || actions.dataset.accessEntryReady === 'true') return;

  const existing = actions.querySelector('a[href="#/sign-in"]');
  if (existing) existing.remove();

  const client = document.createElement('a');
  client.className = 'btn btn-ghost access-client';
  client.href = SIGN_IN;
  client.textContent = 'Client Login';
  client.setAttribute('aria-label', 'Client login');

  const staff = document.createElement('a');
  staff.className = 'btn btn-primary access-staff';
  staff.href = SIGN_IN;
  staff.textContent = 'Staff / Owner';
  staff.setAttribute('aria-label', 'Staff and owner login');

  actions.append(client, staff);
  actions.dataset.accessEntryReady = 'true';
}

function accessSection() {
  const section = document.createElement('section');
  section.id = 'access-entry-section';
  section.className = 'section access-entry-section';
  section.innerHTML = `
    <div class="container">
      <div class="access-entry-heading">
        <div class="eyebrow">Secure access</div>
        <h2>One sign-in. The right workspace opens automatically.</h2>
        <p class="lede">Clients, staff, reviewers, and owners use the same protected sign-in. After authentication, ColettiOS routes each authorized account to its assigned workspace.</p>
      </div>
      <div class="access-entry-grid">
        <article class="access-entry-card">
          <div class="access-entry-number">01</div>
          <h3>Client Portal</h3>
          <p>Open your matter, respond to requests, upload records, review progress, and receive approved deliverables.</p>
          <a class="btn btn-secondary" href="${SIGN_IN}">Enter Client Portal</a>
        </article>
        <article class="access-entry-card access-entry-card-dark">
          <div class="access-entry-number">02</div>
          <h3>Staff &amp; Owner Workspace</h3>
          <p>Authorized team members enter the ColettiOS operations workspace. Owner and administrator accounts route to the command center automatically.</p>
          <a class="btn btn-gold" href="${SIGN_IN}">Enter ColettiOS</a>
        </article>
      </div>
      <p class="access-entry-note">Authentication does not grant authority by itself. Access remains controlled by Supabase identity, role, case membership, staff assignment, and row-level security.</p>
    </div>`;
  return section;
}

function enhanceHome() {
  const main = document.querySelector('#main');
  if (!main) return;
  const isHome = !location.hash || location.hash === '#/home';
  const existing = document.querySelector('#access-entry-section');
  if (!isHome) {
    existing?.remove();
    return;
  }
  if (!existing) main.append(accessSection());
}

function enhance() {
  enhanceHeader();
  enhanceHome();
}

const observer = new MutationObserver(() => enhance());
window.addEventListener('DOMContentLoaded', () => {
  observer.observe(document.body, { childList: true, subtree: true });
  enhance();
});
window.addEventListener('hashchange', enhance);
queueMicrotask(enhance);
