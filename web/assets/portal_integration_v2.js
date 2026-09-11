import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.115.0/+esm';
import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY } from './config.js';

const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
});

const ENTRY_SURFACE = String(window.COLETTI_ENTRY_SURFACE || '').toLowerCase();
const STAFF_ROLES = new Set(['owner','admin','analyst','reviewer']);
const ADMIN_ROLES = new Set(['owner','admin']);
const CHECKPOINTS = [
  {key:'intake', label:'Intake'},
  {key:'engagement', label:'Engagement'},
  {key:'collection', label:'Source Collection'},
  {key:'reconstruction', label:'Reconstruction'},
  {key:'review', label:'Human Review'},
  {key:'report', label:'Report Preparation'},
  {key:'publication', label:'Publication'},
  {key:'closeout', label:'Close / Reopen'}
];

let rendering = false;
let lastSignature = '';

const esc = (v='') => String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const currentRoute = () => (location.hash || '#/home').replace(/^#/, '');
const activeCaseId = () => document.querySelector('#case-selector')?.value || localStorage.getItem('coletti.activeCase') || null;

async function rows(table, select='*', configure=x=>x) {
  try {
    let req = supabase.from(table).select(select);
    req = configure(req);
    const {data,error} = await req;
    if (error) throw error;
    return data || [];
  } catch (error) {
    console.warn(`SOP read failed for ${table}`, error);
    return [];
  }
}

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

function stageRankFromVisibleEvents(events) {
  const text = events.map(x=>`${x.stage||''} ${x.title||''}`.toLowerCase()).join(' | ');
  if (/(closed|closeout|complete|completed|reopened)/.test(text)) return 8;
  if (/(published|final report|delivered)/.test(text)) return 7;
  if (/(report preparation|draft report|reporting|preparation)/.test(text)) return 6;
  if (/(human review|review|qa)/.test(text)) return 5;
  if (/(analysis|reconstruction|reconcile)/.test(text)) return 4;
  if (/(evidence collection|source collection|document collection|collection)/.test(text)) return 3;
  if (/(engagement|accepted engagement)/.test(text)) return 2;
  if (/(intake|submitted)/.test(text)) return 1;
  return 0;
}

const stateOf = (done, active=false, blocked=false) => blocked ? 'blocked' : done ? 'done' : active ? 'active' : 'pending';

async function clientProgress(ctx) {
  const c = ctx.caseId;
  const [intakes, engagements, uploads, requests, events, reports] = await Promise.all([
    rows('intake_submissions','id,status,case_id,submitted_at',x=>x.eq('user_id',ctx.user.id).order('created_at',{ascending:false}).limit(20)),
    rows('engagement_acceptances','id,case_id,accepted,accepted_at',x=>x.eq('user_id',ctx.user.id).order('created_at',{ascending:false}).limit(20)),
    rows('upload_records','id,case_id,status,created_at',x=>x.eq('case_id',c).order('created_at',{ascending:false})),
    rows('document_requests','id,case_id,status,client_visible',x=>x.eq('case_id',c).eq('client_visible',true)),
    rows('case_status_events','id,stage,title,occurred_at,client_visible',x=>x.eq('case_id',c).eq('client_visible',true).order('occurred_at',{ascending:false})),
    rows('published_reports','id,case_id,published_at,client_visible,revoked_at',x=>x.eq('case_id',c).eq('client_visible',true).is('revoked_at',null))
  ]);
  const intake = intakes.some(x=>!c || x.case_id===c || !x.case_id);
  const engagement = engagements.some(x=>x.accepted && (!c || x.case_id===c || !x.case_id));
  const openRequests = requests.filter(x=>!['SATISFIED','WAIVED','COMPLETE','COMPLETED'].includes(String(x.status||'').toUpperCase())).length;
  const collectionStarted = uploads.length > 0 || requests.length > 0;
  const collectionDone = uploads.length > 0 && openRequests === 0;
  const rank = stageRankFromVisibleEvents(events);
  const published = reports.length > 0;
  const closed = rank >= 8;
  const raw = [
    stateOf(intake, !intake),
    stateOf(engagement, intake && !engagement),
    stateOf(collectionDone, engagement && collectionStarted && !collectionDone),
    stateOf(rank >= 4, collectionDone && rank < 4),
    stateOf(rank >= 5, rank === 4),
    stateOf(rank >= 6, rank === 5),
    stateOf(published, rank >= 6 && !published),
    stateOf(closed, published && !closed)
  ];
  return {states:raw, note:openRequests?`${openRequests} requested record${openRequests===1?'':'s'} still open.`:'Client view shows only client-visible case state.'};
}

async function internalProgress(ctx) {
  const c = ctx.caseId;
  const [intakes, engagements, uploads, requests, work, narratives, qa, handoffs, reports, events] = await Promise.all([
    rows('intake_submissions','id,status,case_id',x=>x.eq('case_id',c).order('created_at',{ascending:false})),
    rows('engagement_acceptances','id,case_id,accepted,accepted_at',x=>x.eq('case_id',c).eq('accepted',true)),
    rows('upload_records','id,status,source_id,case_id',x=>x.eq('case_id',c)),
    rows('document_requests','id,status,client_visible,case_id',x=>x.eq('case_id',c)),
    rows('evidence_work_items','id,queue_type,status,evidence_state,case_id',x=>x.eq('case_id',c)),
    rows('review_narratives','id,status,case_id',x=>x.eq('case_id',c)),
    rows('qa_checklists','id,status,item_key,case_id',x=>x.eq('case_id',c)),
    rows('publication_handoffs','id,status,approved_at,first_truth_preflight_status,professional_boundary_passed,case_id',x=>x.eq('case_id',c).order('created_at',{ascending:false})),
    rows('published_reports','id,published_at,revoked_at,case_id',x=>x.eq('case_id',c).is('revoked_at',null)),
    rows('case_status_events','id,stage,title,occurred_at,client_visible,case_id',x=>x.eq('case_id',c).order('occurred_at',{ascending:false}))
  ]);

  const intakeAccepted = intakes.some(x=>['ACCEPTED','COMPLETE','COMPLETED'].includes(String(x.status||'').toUpperCase()));
  const intakeStarted = intakes.length > 0;
  const engagementDone = engagements.length > 0;
  const openRequests = requests.filter(x=>!['SATISFIED','WAIVED','COMPLETE','COMPLETED'].includes(String(x.status||'').toUpperCase())).length;
  const registeredUploads = uploads.filter(x=>x.source_id || ['INGESTED','REGISTERED','PROCESSED'].includes(String(x.status||'').toUpperCase())).length;
  const collectionStarted = uploads.length > 0 || requests.length > 0;
  const collectionDone = uploads.length > 0 && openRequests === 0;
  const reconstructionStarted = work.length > 0;
  const reconstructionOpen = work.filter(x=>['OPEN','IN_REVIEW','PENDING'].includes(String(x.status||'').toUpperCase())).length;
  const reconstructionDone = reconstructionStarted && reconstructionOpen === 0;
  const narrativeReady = narratives.some(x=>['FINAL_INTERNAL','READY_FOR_QA','APPROVED'].includes(String(x.status||'').toUpperCase()));
  const qaFailures = qa.filter(x=>String(x.status||'').toUpperCase()==='FAIL').length;
  const qaPending = qa.filter(x=>String(x.status||'').toUpperCase()==='PENDING').length;
  const qaDone = qa.length > 0 && qaFailures === 0 && qaPending === 0;
  const reviewDone = narrativeReady && qaDone;
  const latestHandoff = handoffs[0];
  const reportStarted = handoffs.length > 0;
  const reportDone = handoffs.some(x=>['APPROVED','PUBLISHED','READY_TO_PUBLISH'].includes(String(x.status||'').toUpperCase()) && String(x.first_truth_preflight_status||'').toUpperCase()!=='FAIL');
  const published = reports.length > 0;
  const visibleRank = stageRankFromVisibleEvents(events);
  const closed = visibleRank >= 8;
  const blockedReview = qaFailures > 0;
  const blockedReport = latestHandoff && (String(latestHandoff.first_truth_preflight_status||'').toUpperCase()==='FAIL' || latestHandoff.professional_boundary_passed===false);

  const states = [
    stateOf(intakeAccepted, intakeStarted && !intakeAccepted),
    stateOf(engagementDone, intakeAccepted && !engagementDone),
    stateOf(collectionDone, engagementDone && collectionStarted && !collectionDone),
    stateOf(reconstructionDone, collectionDone && reconstructionStarted && !reconstructionDone),
    stateOf(reviewDone, reconstructionDone && !reviewDone, blockedReview),
    stateOf(reportDone, reviewDone && reportStarted && !reportDone, blockedReport),
    stateOf(published, reportDone && !published),
    stateOf(closed, published && !closed)
  ];
  const blockers = [];
  if (openRequests) blockers.push(`${openRequests} open document request${openRequests===1?'':'s'}`);
  if (reconstructionOpen) blockers.push(`${reconstructionOpen} open reconstruction item${reconstructionOpen===1?'':'s'}`);
  if (qaFailures) blockers.push(`${qaFailures} failed QA checkpoint${qaFailures===1?'':'s'}`);
  if (blockedReport) blockers.push('publication preflight blocked');
  if (!registeredUploads && uploads.length) blockers.push('uploads not yet source-registered');
  return {states, note:blockers.length?blockers.join(' · '):'No checkpoint blocker is visible in the current authoritative records.'};
}

function checkpointHref(key, ctx) {
  if (ctx.surface === 'client') {
    return {
      intake:'#/portal/intake', engagement:'#/portal/engagement', collection:'#/portal/uploads', reconstruction:'#/portal/timeline',
      review:'#/portal/timeline', report:'#/portal/timeline', publication:'#/portal/reports', closeout:'#/portal/timeline'
    }[key];
  }
  const adminLike = ADMIN_ROLES.has(ctx.role);
  return {
    intake:'#/workspace/intake', engagement:'#/workspace/home', collection:'#/workspace/documents', reconstruction:'#/workspace/evidence',
    review:'#/workspace/qa', report:'#/workspace/publishing', publication:adminLike?'#/admin/publications':'#/workspace/publishing', closeout:'#/workspace/notes'
  }[key];
}

function renderSop(ctx, progress) {
  if (!ctx.caseId) return '';
  const firstOpen = progress.states.findIndex(x=>x!=='done');
  const completed = progress.states.filter(x=>x==='done').length;
  return `<section class="case-sop" data-case-sop="v2">
    <div class="case-sop-head"><div><div class="portal-surface-kicker">CASE STANDARD OPERATING PROCEDURE</div><h2 class="case-sop-title">${esc(ctx.caseId)} · Case Progress</h2><div class="case-sop-meta">${completed} of ${CHECKPOINTS.length} checkpoints complete · one authoritative case state across authorized portals</div></div><a class="case-sop-link" href="${ctx.surface==='client'?'#/portal/timeline':'#/workspace/home'}">View case workspace →</a></div>
    <div class="case-sop-track">${CHECKPOINTS.map((cp,i)=>{
      let st=progress.states[i]||'pending';
      if(st==='pending' && i===firstOpen) st='active';
      return `<a class="case-sop-step ${st}" href="${checkpointHref(cp.key,ctx)}" title="Open ${esc(cp.label)} checkpoint"><span class="case-sop-dot"></span><span>${esc(cp.label)}</span><span class="case-sop-state">${st==='done'?'Complete':st==='blocked'?'Blocked':st==='active'?'Current':'Pending'}</span></a>`;
    }).join('')}</div>
    <div class="case-sop-foot"><span>Dashboard status is derived from canonical records; it does not create a second workflow.</span><span class="${/blocked|open|failed/i.test(progress.note)?'case-sop-warning':''}">${esc(progress.note)}</span></div>
  </section>`;
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
  const progress = ctx.surface==='client' ? await clientProgress(ctx) : await internalProgress(ctx);
  topbar.insertAdjacentHTML('afterend', renderSop(ctx, progress));
}

async function enhance() {
  if (rendering) return;
  rendering = true;
  try {
    const shell = document.querySelector('.workspace-shell');
    if (!shell) return;
    const ctx = await context();
    if (!ctx.user) return;
    decorateChrome(ctx);
    await decorateSop(ctx);
  } finally {
    rendering = false;
  }
}

function scheduleEnhance() {
  queueMicrotask(()=>void enhance());
}

const observer = new MutationObserver(()=>scheduleEnhance());
observer.observe(document.documentElement,{childList:true,subtree:true});
window.addEventListener('hashchange',()=>{lastSignature='';scheduleEnhance();});
document.addEventListener('change',e=>{if(e.target?.id==='case-selector'){lastSignature='';scheduleEnhance();}});
supabase.auth.onAuthStateChange(()=>{lastSignature='';scheduleEnhance();});
window.addEventListener('DOMContentLoaded',scheduleEnhance);
scheduleEnhance();
