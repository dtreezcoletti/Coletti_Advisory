import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.115.0/+esm';
import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY } from './config.js';

const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
});

const ENTRY_SURFACE = String(window.COLETTI_ENTRY_SURFACE || '').toLowerCase();
const STAFF_ROLES = new Set(['owner','admin','analyst','reviewer']);
const ADMIN_ROLES = new Set(['owner','admin']);
const COMPLETE_STATES = new Set(['COMPLETE','NOT_APPLICABLE']);
const ACTIVE_STATES = new Set(['READY','IN_PROGRESS','WAITING','AWAITING_HUMAN']);
let rendering = false;
let lastSignature = '';

const esc = (v='') => String(v ?? '').replace(/[&<>'\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','\"':'&quot;'}[c]));
const currentRoute = () => (location.hash || '#/home').replace(/^#/, '');
const activeCaseId = () => document.querySelector('#case-selector')?.value || localStorage.getItem('coletti.activeCase') || null;

async function context() {
  const {data} = await supabase.auth.getSession();
  const user = data?.session?.user || null;
  if (!user) return {user:null, profile:null, role:null, surface:'client', caseId:null};
  const {data:profile} = await supabase.from('profiles').select('id,role,display_name').eq('id',user.id).maybeSingle();
  const role = profile?.role || 'client';
  let surface = 'client';
  if (role === 'owner' && ENTRY_SURFACE === 'owner') surface = 'owner';
  else if (ADMIN_ROLES.has(role)) surface = ENTRY_SURFACE === 'employee' ? 'employee' : 'admin';
  else if (STAFF_ROLES.has(role)) surface = 'employee';
  return {user, profile:profile || {role}, role, surface, caseId:activeCaseId()};
}

function surfaceLabel(ctx) {
  if (ctx.surface === 'owner') return 'Owner Portal';
  if (ctx.surface === 'admin') return 'Admin Portal';
  if (ctx.surface === 'employee') return 'Employee Portal';
  return 'Client Portal';
}

function kickerFor(ctx) {
  if (ctx.surface === 'owner') return 'OWNER PORTAL · GOVERNANCE & OVERSIGHT';
  if (ctx.surface === 'admin') return 'ADMIN PORTAL · OPERATING CONTROL';
  if (ctx.surface === 'employee') return 'EMPLOYEE PORTAL · CASE OPERATIONS';
  return 'CLIENT PORTAL · AUTHORIZED WORKSPACE';
}

function switcher(ctx) {
  const items = [];
  if (ctx.role === 'owner') {
    items.push(['owner','/owner/#/admin/home','Owner']);
    items.push(['admin','/admin/#/admin/home','Admin']);
    items.push(['employee','/employee/#/workspace/home','Employee']);
  } else if (ctx.role === 'admin') {
    items.push(['admin','/admin/#/admin/home','Admin']);
    items.push(['employee','/employee/#/workspace/home','Employee']);
  } else if (STAFF_ROLES.has(ctx.role)) {
    items.push(['employee','/employee/#/workspace/home','Employee']);
  } else {
    items.push(['client','/portal/#/portal/home','Client']);
  }
  if (items.length < 2) return '';
  return `<div class="portal-switcher">${items.map(([id,href,label])=>`<a href="${href}" ${ctx.surface===id?'aria-current="page"':''}>${label}</a>`).join('')}</div>`;
}

function decorateChrome(ctx) {
  const sidebar = document.querySelector('.workspace-sidebar');
  if (!sidebar) return;
  if (!sidebar.querySelector('.portal-brand-block')) {
    sidebar.insertAdjacentHTML('afterbegin', `<div class="portal-brand-block"><img src="/assets/coletti-logo.webp" alt="Coletti & Co."><div class="portal-brand-tagline">Records · Clarity · Forward.</div></div>${switcher(ctx)}`);
  }
  const title = sidebar.querySelector('.workspace-title');
  if (title) title.textContent = surfaceLabel(ctx);
  const role = sidebar.querySelector('.workspace-role');
  if (role && ctx.profile?.display_name) role.textContent = `${String(ctx.role || '').replace('_',' ')} · ${ctx.profile.display_name}`;
  const headingWrap = document.querySelector('.workspace-topbar > div:first-child');
  if (headingWrap && !headingWrap.querySelector('.portal-surface-kicker')) {
    headingWrap.insertAdjacentHTML('afterbegin', `<div class="portal-surface-kicker">${esc(kickerFor(ctx))}</div>`);
  }
}

async function lifecycleSnapshot(caseId) {
  const {data,error} = await supabase.rpc('case_lifecycle_snapshot_v1',{p_case_id:caseId});
  if (error) throw error;
  return data;
}

function checkpointClass(status, currentKey, key) {
  const normalized = String(status || 'NOT_STARTED').toUpperCase();
  if (normalized === 'BLOCKED') return 'blocked';
  if (COMPLETE_STATES.has(normalized)) return 'done';
  if (key === currentKey || ACTIVE_STATES.has(normalized)) return 'active';
  return 'pending';
}

function checkpointHref(key, ctx) {
  if (ctx.surface === 'client') {
    return ({
      INTAKE:'#/portal/intake', SCREENING:'#/portal/intake', ACCEPTANCE:'#/portal/intake',
      CLIENT_ONBOARDING:'#/portal/profile', ENGAGEMENT_GATES:'#/portal/engagement', CASE_OPENING:'#/portal/home',
      RECORD_COLLECTION:'#/portal/uploads', RECONSTRUCTION:'#/portal/timeline', HUMAN_REVIEW:'#/portal/timeline',
      REPORT_PREPARATION:'#/portal/timeline', PUBLICATION_HANDOFF:'#/portal/reports', CLOSEOUT:'#/portal/timeline', ARCHIVE:'#/portal/timeline'
    })[key] || '#/portal/home';
  }
  const adminLike = ADMIN_ROLES.has(ctx.role);
  return ({
    INTAKE:'#/workspace/intake', SCREENING:'#/workspace/intake', ACCEPTANCE:'#/workspace/intake',
    CLIENT_ONBOARDING:adminLike?'#/admin/assignments':'#/workspace/home', ENGAGEMENT_GATES:'#/workspace/intake',
    CASE_OPENING:adminLike?'#/admin/assignments':'#/workspace/home', RECORD_COLLECTION:'#/workspace/documents',
    RECONSTRUCTION:'#/workspace/evidence', HUMAN_REVIEW:'#/workspace/qa', REPORT_PREPARATION:'#/workspace/publishing',
    PUBLICATION_HANDOFF:adminLike?'#/admin/publications':'#/workspace/publishing', CLOSEOUT:adminLike?'#/admin/audit':'#/workspace/notes',
    ARCHIVE:adminLike?'#/admin/audit':'#/workspace/notes'
  })[key] || '#/workspace/home';
}

function renderSop(ctx, snapshot) {
  const checkpoints = Array.isArray(snapshot?.checkpoints) ? snapshot.checkpoints : [];
  const currentKey = snapshot?.case?.current_checkpoint || null;
  const completeCount = checkpoints.filter(cp=>COMPLETE_STATES.has(String(cp.status||'').toUpperCase())).length;
  const blocked = checkpoints.filter(cp=>String(cp.status||'').toUpperCase()==='BLOCKED');
  const openRequests = Number(snapshot?.open_requests || 0);
  const publishedReports = Number(snapshot?.published_reports || 0);
  const noteBits = [];
  if (blocked.length) noteBits.push(`${blocked.length} blocked checkpoint${blocked.length===1?'':'s'}`);
  if (openRequests) noteBits.push(`${openRequests} open record request${openRequests===1?'':'s'}`);
  if (publishedReports) noteBits.push(`${publishedReports} published report${publishedReports===1?'':'s'}`);
  if (!noteBits.length) noteBits.push(`Case status: ${snapshot?.case?.status || 'OPEN'}`);
  return `<section class="case-sop" data-case-sop="v2">
    <div class="case-sop-head"><div><div class="portal-surface-kicker">CASE STANDARD OPERATING PROCEDURE</div><h2 class="case-sop-title">${esc(snapshot?.case?.case_id || ctx.caseId)} · Case Progress</h2><div class="case-sop-meta">${completeCount} of ${checkpoints.length} checkpoints complete · authoritative lifecycle state shared across authorized portals</div></div><a class="case-sop-link" href="${ctx.surface==='client'?'#/portal/timeline':'#/workspace/home'}">View case workspace →</a></div>
    <div class="case-sop-track">${checkpoints.map(cp=>{
      const st = checkpointClass(cp.status,currentKey,cp.key);
      const detail = cp.public_note || cp.description || '';
      return `<a class="case-sop-step ${st}" href="${checkpointHref(cp.key,ctx)}" title="${esc(detail || cp.label)}"><span class="case-sop-dot"></span><span>${esc(cp.label)}</span><span class="case-sop-state">${esc(cp.status || 'NOT_STARTED').replaceAll('_',' ')}</span></a>`;
    }).join('')}</div>
    <div class="case-sop-foot"><span>Each checkpoint opens the canonical workspace that owns that work; the dashboard does not create duplicate case state.</span><span class="${blocked.length||openRequests?'case-sop-warning':''}">${esc(noteBits.join(' · '))}</span></div>
  </section>`;
}

function renderSopError(ctx, error) {
  return `<section class="case-sop" data-case-sop="v2"><div class="case-sop-head"><div><div class="portal-surface-kicker">CASE STANDARD OPERATING PROCEDURE</div><h2 class="case-sop-title">${esc(ctx.caseId)} · Lifecycle unavailable</h2><div class="case-sop-meta">The portal remains available, but authoritative checkpoint state could not be loaded.</div></div></div><div class="notice notice-warning">${esc(error?.message || 'Lifecycle state could not be read.')}</div></section>`;
}

async function decorateSop(ctx) {
  const main = document.querySelector('.workspace-main');
  if (!main || !ctx.caseId) return;
  const signature = `${ctx.user?.id||''}|${ctx.role}|${ctx.surface}|${ctx.caseId}|${currentRoute()}`;
  if (signature === lastSignature && main.querySelector('[data-case-sop="v2"]')) return;
  lastSignature = signature;
  main.querySelector('[data-case-sop="v2"]')?.remove();
  const topbar = main.querySelector('.workspace-topbar');
  if (!topbar) return;
  try {
    const snapshot = await lifecycleSnapshot(ctx.caseId);
    topbar.insertAdjacentHTML('afterend', renderSop(ctx,snapshot));
  } catch (error) {
    console.error('Authoritative lifecycle read failed',error);
    topbar.insertAdjacentHTML('afterend', renderSopError(ctx,error));
  }
}

async function enhance() {
  if (rendering) return;
  rendering = true;
  try {
    if (!document.querySelector('.workspace-shell')) return;
    const ctx = await context();
    if (!ctx.user) return;
    decorateChrome(ctx);
    await decorateSop(ctx);
  } finally { rendering = false; }
}

function scheduleEnhance() { queueMicrotask(()=>void enhance()); }
const observer = new MutationObserver(()=>scheduleEnhance());
observer.observe(document.documentElement,{childList:true,subtree:true});
window.addEventListener('hashchange',()=>{lastSignature='';scheduleEnhance();});
document.addEventListener('change',e=>{if(e.target?.id==='case-selector'){lastSignature='';scheduleEnhance();}});
supabase.auth.onAuthStateChange(()=>{lastSignature='';scheduleEnhance();});
window.addEventListener('DOMContentLoaded',scheduleEnhance);
scheduleEnhance();
