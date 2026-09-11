import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.115.0/+esm';
import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY } from './config.js';

const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
});

const $ = (selector, root=document) => root.querySelector(selector);
const esc = (value='') => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}[char]));
const fmtDate = value => value ? new Intl.DateTimeFormat('en-US', {
  month:'short', day:'numeric', year:'numeric', hour:'numeric', minute:'2-digit'
}).format(new Date(value)) : '—';

function route() {
  return (location.hash || '#/home').replace(/^#/, '');
}

async function ownerSession() {
  const { data } = await supabase.auth.getSession();
  const user = data?.session?.user;
  if (!user) return false;
  const { data: profile } = await supabase.from('profiles').select('role').eq('id', user.id).maybeSingle();
  return profile?.role === 'owner';
}

function governanceNav() {
  return `<nav class="owner-governance-nav" aria-label="Owner governance">
    <a class="btn btn-secondary" href="#/admin/home">Command Center</a>
    <a class="btn btn-secondary" href="#/admin/docket">Docket</a>
    <a class="btn btn-secondary" href="#/admin/implementation">Implementation Matrix</a>
  </nav>`;
}

function shell(title, lede, body) {
  const main = $('#main');
  if (!main) return;
  main.innerHTML = `<section class="section section-ivory"><div class="container">
    ${governanceNav()}
    <div class="eyebrow">Owner · Company Control</div>
    <h1>${esc(title)}</h1>
    <p class="lede">${esc(lede)}</p>
    <div class="mt-2">${body}</div>
  </div></section>`;
}

function stateBadge(value) {
  const safe = esc(value || 'UNKNOWN');
  return `<span class="badge">${safe}</span>`;
}

async function renderDocket() {
  shell('Docket', 'Authoritative governance documents, controlled state, and owner-approved transitions.', '<div class="card">Loading authoritative Docket…</div>');
  const { data, error } = await supabase.rpc('owner_docket_snapshot');
  if (error) {
    shell('Docket', 'Authoritative governance documents, controlled state, and owner-approved transitions.', `<div class="notice notice-error">${esc(error.message || 'Docket access failed.')}</div>`);
    return;
  }
  const docs = data?.documents || [];
  const rows = docs.map(doc => `<tr>
    <td><strong>${esc(doc.title)}</strong><div class="small muted">${esc(doc.document_key)}</div></td>
    <td>${esc(doc.document_type)}</td>
    <td>${stateBadge(doc.document_state)}</td>
    <td>${esc(doc.version)}</td>
    <td>${esc(doc.authority || '—')}</td>
    <td>${esc(fmtDate(doc.updated_at))}</td>
  </tr>`).join('');
  const options = docs.map(doc => `<option value="${esc(doc.document_key)}">${esc(doc.title)} · ${esc(doc.document_state)}</option>`).join('');
  const counts = Object.entries(data?.state_counts || {}).map(([key,value]) => `<span class="badge">${esc(key)} · ${esc(value)}</span>`).join(' ');
  shell('Docket', 'Authoritative governance documents, controlled state, and owner-approved transitions.', `
    <div class="card"><div class="eyebrow">Current State</div><div class="evidence-badges mt-1">${counts || '<span class="muted">No Docket documents.</span>'}</div></div>
    <div class="table-wrap mt-2"><table><thead><tr><th>Document</th><th>Type</th><th>State</th><th>Version</th><th>Authority</th><th>Updated</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="card mt-2">
      <div class="eyebrow">Controlled Transition</div>
      <h3>Owner action</h3>
      <p class="muted">Every transition requires an explicit human reason and is written through the authoritative Registry with audit history. No document is promoted automatically.</p>
      <label>Document<select id="docket-document" class="input">${options}</select></label>
      <label>Target state<select id="docket-target" class="input"><option>DRAFT</option><option>MASTER</option><option>SUPERSEDED</option><option>RETIRED</option></select></label>
      <label>Reason<textarea id="docket-reason" class="input" rows="3" placeholder="Required human rationale"></textarea></label>
      <button id="docket-transition" class="btn btn-primary">Apply controlled transition</button>
      <div id="docket-result" class="small mt-1" aria-live="polite"></div>
    </div>
    <div class="notice notice-info mt-2"><strong>Professional firewall.</strong> ${esc(data?.protected_profession_rule || '')}</div>
  `);

  $('#docket-transition')?.addEventListener('click', async () => {
    const key = $('#docket-document')?.value || '';
    const target = $('#docket-target')?.value || '';
    const reason = ($('#docket-reason')?.value || '').trim();
    const result = $('#docket-result');
    if (!reason) {
      if (result) result.textContent = 'A human reason is required.';
      return;
    }
    if (result) result.textContent = 'Applying controlled transition…';
    const { error: transitionError } = await supabase.rpc('owner_docket_transition', {
      p_document_key: key,
      p_target_state: target,
      p_reason: reason
    });
    if (transitionError) {
      if (result) result.textContent = transitionError.message || 'Transition failed.';
      return;
    }
    await renderDocket();
  });
}

async function renderImplementation() {
  shell('Implementation Matrix', 'Policy-to-System Parity and implementation lifecycle from Proposed through Operational.', '<div class="card">Loading authoritative Implementation Matrix…</div>');
  const { data, error } = await supabase.rpc('owner_implementation_snapshot');
  if (error) {
    shell('Implementation Matrix', 'Policy-to-System Parity and implementation lifecycle from Proposed through Operational.', `<div class="notice notice-error">${esc(error.message || 'Implementation Matrix access failed.')}</div>`);
    return;
  }
  const items = data?.items || [];
  const counts = Object.entries(data?.state_counts || {}).map(([key,value]) => `<span class="badge">${esc(key)} · ${esc(value)}</span>`).join(' ');
  const rows = items.map(item => `<tr>
    <td><strong>${esc(item.implementation_id)}</strong></td>
    <td><strong>${esc(item.requirement_title)}</strong><div class="small muted">${esc(item.source_record_key || '')}</div></td>
    <td>${stateBadge(item.implementation_state)}</td>
    <td>${esc(item.policy_status)}</td>
    <td>${esc(item.database_status)}</td>
    <td>${esc(item.code_status)}</td>
    <td>${esc(item.workflow_status)}</td>
    <td>${esc(item.human_control_status)}</td>
    <td>${esc(item.test_status)}</td>
    <td>${esc(item.documentation_status)}</td>
    <td>${esc(item.blocker || item.next_action || '—')}</td>
  </tr>`).join('');
  shell('Implementation Matrix', 'Policy-to-System Parity and implementation lifecycle from Proposed through Operational.', `
    <div class="card"><div class="eyebrow">Lifecycle</div><p><strong>${esc((data?.lifecycle || []).join(' → '))}</strong></p><div class="evidence-badges">${counts}</div></div>
    <div class="table-wrap mt-2"><table><thead><tr><th>ID</th><th>Requirement</th><th>State</th><th>Policy</th><th>DB</th><th>Code</th><th>Workflow</th><th>Human</th><th>Tests</th><th>Docs</th><th>Blocker / Next action</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="notice notice-info mt-2">This surface is deliberately read-only. Implementation promotion remains a controlled institutional action; the UI does not silently promote an item because code or a database migration exists.</div>
  `);
}

async function ensureOwnerLinks() {
  if (!(await ownerSession())) return;
  const actions = $('.header-actions');
  if (!actions || $('#owner-governance-entry')) return;
  const link = document.createElement('a');
  link.id = 'owner-governance-entry';
  link.className = 'btn btn-ghost desktop-only';
  link.href = '#/admin/docket';
  link.textContent = 'Company Control';
  actions.prepend(link);
}

async function renderOwnerGovernanceRoute() {
  const current = route();
  if (!['/admin/docket','/admin/implementation'].includes(current)) {
    await ensureOwnerLinks();
    return;
  }
  if (!(await ownerSession())) {
    location.hash = '#/sign-in';
    return;
  }
  if (current === '/admin/docket') await renderDocket();
  else await renderImplementation();
}

let scheduled = false;
function schedule() {
  if (scheduled) return;
  scheduled = true;
  setTimeout(async () => {
    scheduled = false;
    await renderOwnerGovernanceRoute();
  }, 60);
}

window.addEventListener('DOMContentLoaded', schedule);
window.addEventListener('hashchange', schedule);
supabase.auth.onAuthStateChange(() => schedule());
new MutationObserver(() => {
  if (!scheduled && !['/admin/docket','/admin/implementation'].includes(route())) schedule();
}).observe(document.documentElement, { subtree:true, childList:true });

schedule();
