import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.115.0/+esm';
import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY } from './config.js';

const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
});

const STAFF = new Set(['owner','admin','analyst','reviewer']);
const ADMIN = new Set(['owner','admin']);
let rendering = false;

const esc = (value='') => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}[char]));
const route = () => (location.hash || '#/home').replace(/^#/, '');
const label = value => String(value || '').replaceAll('_',' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
const statusIcon = value => ({COMPLETE:'✓',IN_PROGRESS:'◐',READY:'→',WAITING:'◷',AWAITING_HUMAN:'!',BLOCKED:'×',NOT_APPLICABLE:'—'}[value] || '○');

async function context() {
  const { data } = await supabase.auth.getSession();
  const user = data?.session?.user;
  if (!user) return null;
  const { data: profile, error } = await supabase.from('profiles').select('role,display_name').eq('id',user.id).maybeSingle();
  if (error) throw error;
  const role = profile?.role || 'client';
  let rows = [];
  if (ADMIN.has(role)) {
    const [assignments, memberships] = await Promise.all([
      supabase.from('case_assignments').select('case_id').eq('active',true),
      supabase.from('case_memberships').select('case_id').eq('active',true),
    ]);
    if (assignments.error) throw assignments.error;
    if (memberships.error) throw memberships.error;
    rows = [...(assignments.data || []), ...(memberships.data || [])];
  } else if (STAFF.has(role)) {
    const result = await supabase.from('case_assignments').select('case_id').eq('staff_user_id',user.id).eq('active',true);
    if (result.error) throw result.error;
    rows = result.data || [];
  } else {
    const result = await supabase.from('case_memberships').select('case_id').eq('user_id',user.id).eq('active',true);
    if (result.error) throw result.error;
    rows = result.data || [];
  }
  const caseIds = [...new Set(rows.map(row => row.case_id).filter(Boolean))];
  let activeCase = localStorage.getItem('coletti.activeCase');
  if (!activeCase || !caseIds.includes(activeCase)) activeCase = caseIds[0] || null;
  if (activeCase) localStorage.setItem('coletti.activeCase',activeCase);
  return { user, profile: profile || {}, role, caseIds, activeCase };
}

async function snapshot(caseId) {
  const { data, error } = await supabase.rpc('case_lifecycle_snapshot_v1',{p_case_id:caseId});
  if (error) throw error;
  return data || {};
}

function lifecycleRows(data) {
  const items = data?.checkpoints || [];
  if (!items.length) return '<div class="empty">No lifecycle checkpoints are available.</div>';
  return `<div class="table-wrap"><table class="dense"><thead><tr><th></th><th>Checkpoint</th><th>Status</th><th>Context</th></tr></thead><tbody>${items.map(item => `<tr>
    <td><strong>${esc(statusIcon(item.status))}</strong></td>
    <td><strong>${esc(item.label)}</strong><div class="micro">${esc(item.domain || '')}${item.protected_gate?' · Protected gate':''}</div></td>
    <td><span class="badge">${esc(label(item.status))}</span></td>
    <td>${esc(item.public_note || item.description || '')}</td>
  </tr>`).join('')}</tbody></table></div>`;
}

function controls(ctx, data) {
  if (!STAFF.has(ctx.role)) return '';
  const allowed = ctx.role === 'analyst' || ctx.role === 'reviewer'
    ? (data.checkpoints || []).filter(item => ['RECORD_COLLECTION','RECONSTRUCTION','HUMAN_REVIEW','REPORT_PREPARATION'].includes(item.key))
    : (data.checkpoints || []);
  if (!allowed.length) return '';
  return `<div class="divider"></div><div class="eyebrow">Checkpoint Control</div>
    <form id="lifecycle-transition-form" class="mt-1">
      <div class="form-grid">
        <div class="form-field"><label>Checkpoint</label><select name="checkpoint_key">${allowed.map(item => `<option value="${esc(item.key)}">${esc(item.label)} · ${esc(label(item.status))}</option>`).join('')}</select></div>
        <div class="form-field"><label>Target state</label><select name="target_status">${['NOT_STARTED','READY','IN_PROGRESS','WAITING','BLOCKED','AWAITING_HUMAN','COMPLETE','NOT_APPLICABLE'].map(value=>`<option>${value}</option>`).join('')}</select></div>
        <div class="form-field"><label>Human rationale</label><input name="reason" placeholder="Required for completion / blocked / N/A" /></div>
        <div class="form-field"><label>Client-visible note</label><input name="public_note" placeholder="Optional factual update" /></div>
      </div><div class="form-actions"><button class="btn btn-primary" type="submit">Record checkpoint transition</button></div>
    </form>`;
}

function lifecyclePanel(ctx, data, full=false) {
  const current = data?.case?.current_checkpoint ? label(data.case.current_checkpoint) : 'Complete';
  const casePicker = ctx.caseIds.length > 1 ? `<select id="lifecycle-case-selector" style="width:auto;min-width:180px">${ctx.caseIds.map(id=>`<option value="${esc(id)}" ${id===ctx.activeCase?'selected':''}>${esc(id)}</option>`).join('')}</select>` : '';
  return `<section class="panel" data-lifecycle-v1="true">
    <div class="panel-head"><div><div class="eyebrow">Case Control · SOP Checkpoints</div><h3>${full?'Case Lifecycle':'Lifecycle Checkpoints'}</h3><div class="panel-sub">One authoritative state across Client, Employee, Admin, and Owner · Current: ${esc(current)}</div></div>${casePicker}</div>
    ${lifecycleRows(data)}
    ${controls(ctx,data)}
  </section>`;
}

function addEyebrow(ctx) {
  const topbar = document.querySelector('.workspace-topbar > div:first-child');
  if (!topbar || topbar.querySelector('[data-portal-eyebrow]')) return;
  const text = ctx.role === 'owner' ? 'Owner Console' : ctx.role === 'admin' ? 'Admin Console' : STAFF.has(ctx.role) ? 'Employee Portal' : 'Client Portal';
  const eyebrow = document.createElement('div');
  eyebrow.className = 'eyebrow';
  eyebrow.dataset.portalEyebrow = 'true';
  eyebrow.textContent = text;
  topbar.prepend(eyebrow);
}

async function renderLifecycle() {
  if (rendering) return;
  const r = route();
  if (!r.startsWith('/portal/') && !r.startsWith('/workspace/') && !r.startsWith('/admin/')) return;
  rendering = true;
  try {
    const ctx = await context();
    if (!ctx) return;
    addEyebrow(ctx);
    const main = document.querySelector('.workspace-main');
    if (!main) return;
    main.querySelectorAll('[data-lifecycle-v1]').forEach(node => node.remove());
    if (!ctx.activeCase) return;
    const data = await snapshot(ctx.activeCase);
    const wrapper = document.createElement('div');
    wrapper.dataset.lifecycleV1 = 'true';
    const full = r === '/portal/timeline';
    wrapper.innerHTML = lifecyclePanel(ctx,data,full);
    const topbar = main.querySelector('.workspace-topbar');
    if (topbar?.nextSibling) main.insertBefore(wrapper,topbar.nextSibling); else main.append(wrapper);

    wrapper.querySelector('#lifecycle-case-selector')?.addEventListener('change',event => {
      localStorage.setItem('coletti.activeCase',event.target.value);
      queueMicrotask(() => renderLifecycle());
    });
    wrapper.querySelector('#lifecycle-transition-form')?.addEventListener('submit', async event => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const { error } = await supabase.rpc('transition_case_checkpoint_v1',{
        p_case_id:localStorage.getItem('coletti.activeCase'),
        p_checkpoint_key:form.get('checkpoint_key'),
        p_target_status:form.get('target_status'),
        p_reason:String(form.get('reason') || '') || null,
        p_public_note:String(form.get('public_note') || '') || null,
      });
      if (error) {
        console.error('Lifecycle transition rejected',error);
        alert(error.message.includes('prior lifecycle checkpoint incomplete')
          ? 'A required earlier checkpoint is still unresolved.'
          : error.message);
        return;
      }
      await renderLifecycle();
    });
  } catch (error) {
    console.error('Portal lifecycle integration failed',error);
  } finally {
    rendering = false;
  }
}

let timer = null;
function schedule() {
  clearTimeout(timer);
  timer = setTimeout(() => void renderLifecycle(),80);
}
window.addEventListener('hashchange',schedule);
window.addEventListener('DOMContentLoaded',schedule);
supabase.auth.onAuthStateChange(schedule);
new MutationObserver(schedule).observe(document.documentElement,{subtree:true,childList:true});
schedule();
