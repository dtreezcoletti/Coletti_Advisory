import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.115.0/+esm';
import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY } from './config.js';

const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
});

const STAFF_ROLES = new Set(['owner', 'admin', 'analyst', 'reviewer']);
let lastClient = null;
let profile = null;
let requestGeneration = 0;

const esc = (value = '') => String(value ?? '').replace(/[&<>'"]/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[c]));

function isWorkspaceRoute() {
  return location.hash.startsWith('#/workspace/') || location.hash.startsWith('#/admin/');
}

function port() {
  return document.getElementById('registry-command-port');
}

function shell(inner = '') {
  const root = port();
  if (!root) return;
  root.innerHTML = inner;
}

function hide() {
  requestGeneration += 1;
  shell('');
}

function renderBase(message = 'Search the authoritative registry by client name, Client ID, or ordinary language.') {
  if (!profile || !STAFF_ROLES.has(profile.role) || !isWorkspaceRoute()) {
    hide();
    return;
  }
  shell(`
    <aside aria-label="ColettiOS registry command port" style="position:fixed;right:18px;bottom:18px;z-index:80;width:min(430px,calc(100vw - 36px));background:#fff;border:1px solid rgba(13,36,56,.18);box-shadow:0 18px 42px rgba(13,36,56,.18);border-radius:14px;padding:14px">
      <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:8px">
        <div><strong>ColettiOS Registry</strong><div style="font-size:12px;opacity:.66">Staff command port · read only</div></div>
        <button id="registry-close" type="button" aria-label="Close registry lookup" style="border:0;background:transparent;font-size:20px;cursor:pointer">×</button>
      </div>
      <form id="registry-lookup-form" style="display:flex;gap:8px">
        <input id="registry-query" name="query" autocomplete="off" required placeholder="Find C26-92 or show Jane Smith" style="min-width:0;flex:1" />
        <button type="submit" class="btn btn-primary btn-sm">Search</button>
      </form>
      <div style="font-size:12px;opacity:.7;margin-top:8px">${esc(message)}</div>
      <div id="registry-results" style="margin-top:10px;max-height:300px;overflow:auto"></div>
    </aside>
  `);
  document.getElementById('registry-close')?.addEventListener('click', hide);
  document.getElementById('registry-lookup-form')?.addEventListener('submit', handleLookup);
}

function renderLauncher() {
  if (!profile || !STAFF_ROLES.has(profile.role) || !isWorkspaceRoute()) {
    hide();
    return;
  }
  shell(`<button id="registry-launch" type="button" class="btn btn-primary" style="position:fixed;right:18px;bottom:18px;z-index:80;box-shadow:0 12px 28px rgba(13,36,56,.2)">Registry lookup</button>`);
  document.getElementById('registry-launch')?.addEventListener('click', () => renderBase());
}

async function loadCases(client) {
  const generation = ++requestGeneration;
  lastClient = client;
  const result = document.getElementById('registry-results');
  if (!result) return;
  result.innerHTML = '<div class="small muted">Loading cases…</div>';
  const { data, error } = await supabase.rpc('staff_registry_client_cases', { p_client_id: client.client_id });
  if (generation !== requestGeneration || !document.getElementById('registry-results')) return;
  if (error) {
    result.innerHTML = `<div class="notice notice-danger">${esc(error.message)}</div>`;
    return;
  }
  const rows = data || [];
  result.innerHTML = `
    <div style="margin-bottom:8px"><strong>${esc(client.display_name)}</strong><div class="micro">${esc(client.client_id)}</div></div>
    ${rows.length ? rows.map(row => `
      <div style="padding:9px 0;border-top:1px solid rgba(13,36,56,.1)">
        <strong>${esc(row.case_id)}</strong>
        <span class="badge" style="margin-left:6px">${esc(row.case_status)}</span>
        <div class="micro">Opened ${esc(row.opened_on || '—')}${row.closed_on ? ` · Closed ${esc(row.closed_on)}` : ''}</div>
      </div>
    `).join('') : '<div class="small muted">No registry cases were found for this client.</div>'}
  `;
}

async function handleLookup(event) {
  event.preventDefault();
  const input = document.getElementById('registry-query');
  const result = document.getElementById('registry-results');
  const query = String(input?.value || '').trim();
  if (!query || !result) return;

  if (lastClient && /^(show|open|list)?\s*(their|the)\s*cases\b/i.test(query)) {
    await loadCases(lastClient);
    return;
  }

  const generation = ++requestGeneration;
  result.innerHTML = '<div class="small muted">Searching authoritative registry…</div>';
  const { data, error } = await supabase.rpc('staff_registry_lookup', { p_query: query, p_limit: 10 });
  if (generation !== requestGeneration || !document.getElementById('registry-results')) return;
  if (error) {
    result.innerHTML = `<div class="notice notice-danger">${esc(error.message)}</div>`;
    return;
  }
  const rows = data || [];
  if (!rows.length) {
    lastClient = null;
    result.innerHTML = '<div class="small muted">No matching clients were found.</div>';
    return;
  }
  result.innerHTML = rows.map((row, index) => `
    <button type="button" data-registry-result="${index}" style="display:block;width:100%;text-align:left;padding:10px;border:0;border-top:1px solid rgba(13,36,56,.1);background:transparent;cursor:pointer">
      <strong>${esc(row.display_name)}</strong>
      <div class="micro">${esc(row.client_id)} · ${esc(row.client_status)} · ${esc(row.case_count)} case${Number(row.case_count) === 1 ? '' : 's'}</div>
      <div class="micro">Match: ${esc(row.match_reason)}</div>
    </button>
  `).join('');
  rows.forEach((row, index) => {
    document.querySelector(`[data-registry-result="${index}"]`)?.addEventListener('click', () => loadCases(row));
  });
  lastClient = rows[0];
}

async function refresh() {
  requestGeneration += 1;
  const { data: sessionData } = await supabase.auth.getSession();
  const user = sessionData.session?.user;
  profile = null;
  if (!user) {
    hide();
    return;
  }
  const { data } = await supabase.from('profiles').select('role').eq('id', user.id).maybeSingle();
  profile = data || null;
  renderLauncher();
}

window.addEventListener('hashchange', renderLauncher);
supabase.auth.onAuthStateChange(refresh);
await refresh();
