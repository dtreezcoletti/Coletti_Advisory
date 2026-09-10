import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.115.0/+esm';
import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, APP_NAME } from './config.js';

const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
});

const EVIDENCE_STATES = [
  'Documented Fact','Reconciliation Result','Inconsistency','Missing Documentation',
  'Process Deviation','Unresolved Question','Client Assertion','Third-Party Conclusion','Referral Required'
];
const STAFF_ROLES = ['owner','admin','analyst','reviewer'];
const ADMIN_ROLES = ['owner','admin'];
const state = {
  session: null, user: null, profile: null, services: [], pricing: [], settings: {},
  caseIds: [], activeCase: localStorage.getItem('coletti.activeCase') || null
};
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const esc = (v='') => String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const fmtDate = v => v ? new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric'}).format(new Date(v)) : '—';
const fmtMoney = cents => cents == null ? '—' : new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(Number(cents)/100);
const titleCase = v => String(v || '').toLowerCase().replace(/(^|[_\s-])\w/g, m => m.toUpperCase()).replaceAll('_',' ');
const safeHref = v => /^https:\/\//i.test(String(v || '')) ? String(v) : '#';

function toast(message, kind='') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`; el.textContent = message;
  $('#toast-region')?.append(el); setTimeout(() => el.remove(), 4800);
}
function badge(value) {
  const v = String(value || 'UNKNOWN');
  const low = v.toLowerCase();
  let cls = 'badge-neutral';
  if (/(paid|pass|published|resolved|satisfied|accepted|active|operational|succeeded|approved|complete)/.test(low)) cls='badge-success';
  if (/(open|pending|review|draft|requested|unknown|degraded|waiting|submitted)/.test(low)) cls='badge-warning';
  if (/(fail|critical|outage|rejected|past_due|revoked|suspended|declined)/.test(low)) cls='badge-danger';
  return `<span class="badge ${cls}">${esc(titleCase(v))}</span>`;
}
function evidenceBadge(v) {
  const danger = ['Inconsistency','Missing Documentation','Referral Required'].includes(v);
  const warning = ['Process Deviation','Unresolved Question','Client Assertion','Third-Party Conclusion'].includes(v);
  return `<span class="badge ${danger?'badge-danger':warning?'badge-warning':'badge-success'}">${esc(v)}</span>`;
}
function empty(message) { return `<div class="empty">${esc(message)}</div>`; }
function panel(title, body, sub='', actions='') {
  return `<section class="panel"><div class="panel-head"><div><h3>${esc(title)}</h3>${sub?`<div class="panel-sub">${esc(sub)}</div>`:''}</div>${actions}</div>${body}</section>`;
}
function table(rows, columns, dense=false) {
  if (!rows?.length) return empty('No records are available yet.');
  return `<div class="table-wrap"><table class="${dense?'dense':''}"><thead><tr>${columns.map(c=>`<th>${esc(c.label)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${columns.map(c=>`<td>${c.render?c.render(r):esc(r[c.key] ?? '—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
async function q(tableName, select='*', builder=x=>x) {
  let req = supabase.from(tableName).select(select); req = builder(req);
  const { data, error } = await req; if (error) throw error; return data || [];
}
async function count(tableName, builder=x=>x) {
  let req = supabase.from(tableName).select('*',{count:'exact',head:true}); req=builder(req);
  const { count, error }=await req; if(error) throw error; return count || 0;
}

async function loadPublicData() {
  const [services, pricing, settings] = await Promise.all([
    q('service_definitions','*',x=>x.order('sort_order')),
    q('pricing_config','*',x=>x.order('created_at')),
    q('app_settings','key,value',x=>x.eq('public_read',true))
  ]).catch(err => { console.error(err); return [[],[],[]]; });
  state.services=services; state.pricing=pricing;
  state.settings=Object.fromEntries((settings||[]).map(x=>[x.key,x.value]));
}
async function refreshAuth() {
  const { data } = await supabase.auth.getSession();
  state.session=data.session; state.user=data.session?.user || null; state.profile=null; state.caseIds=[];
  if (!state.user) return;
  const { data:profile, error } = await supabase.from('profiles').select('*').eq('id',state.user.id).maybeSingle();
  if (error) console.error(error); state.profile=profile || {id:state.user.id,display_name:state.user.email,role:'client'};
  await refreshCases();
}
async function refreshCases() {
  if (!state.user) return;
  let ids=[];
  if (ADMIN_ROLES.includes(state.profile?.role)) {
    const [a,m]=await Promise.all([q('case_assignments','case_id'),q('case_memberships','case_id')]).catch(()=>[[],[]]);
    ids=[...a,...m].map(x=>x.case_id);
  } else if (STAFF_ROLES.includes(state.profile?.role)) {
    ids=(await q('case_assignments','case_id',x=>x.eq('staff_user_id',state.user.id).eq('active',true))).map(x=>x.case_id);
  } else {
    ids=(await q('case_memberships','case_id',x=>x.eq('user_id',state.user.id).eq('active',true))).map(x=>x.case_id);
  }
  state.caseIds=[...new Set(ids.filter(Boolean))];
  if (!state.activeCase || !state.caseIds.includes(state.activeCase)) state.activeCase=state.caseIds[0] || null;
  if (state.activeCase) localStorage.setItem('coletti.activeCase',state.activeCase); else localStorage.removeItem('coletti.activeCase');
}

function route() { return (location.hash || '#/home').replace(/^#/, ''); }
function go(path) { location.hash = path.startsWith('/') ? `#${path}` : `#/${path}`; }
function isRole(...roles) { return roles.includes(state.profile?.role); }
function requireAuth() { if(!state.user){ go('/sign-in'); return false;} return true; }
function requireStaff() { if(!requireAuth()) return false; if(!STAFF_ROLES.includes(state.profile?.role)){ go('/portal/home'); return false;} return true; }
function requireAdmin() { if(!requireAuth()) return false; if(!ADMIN_ROLES.includes(state.profile?.role)){ go(STAFF_ROLES.includes(state.profile?.role)?'/workspace/home':'/portal/home'); return false;} return true; }

function renderHeader() {
  const current=route();
  const auth=!!state.user;
  $('#site-header').innerHTML=`<div class="header-inner">
    <a class="brand" href="#/home"><span class="brand-mark">C</span><span><span class="brand-name">Coletti &amp; Co.</span><span class="brand-sub">Evidence Intelligence &amp; Reconstruction</span></span></a>
    <nav class="primary-nav" aria-label="Primary">
      ${[['/services','Services'],['/how-it-works','How It Works'],['/about','About'],['/referral-partners','Referral Partners'],['/pricing','Pricing'],['/security','Security']].map(([p,l])=>`<a href="#${p}" ${current===p?'aria-current="page"':''}>${l}</a>`).join('')}
    </nav>
    <div class="header-actions">
      <a class="btn btn-ghost desktop-only" href="#/contact">Request Consultation</a>
      ${auth?`<a class="btn btn-primary" href="#/${ADMIN_ROLES.includes(state.profile?.role)?'admin/home':STAFF_ROLES.includes(state.profile?.role)?'workspace/home':'portal/home'}">${esc(state.profile?.display_name || 'Workspace')}</a>`:`<a class="btn btn-primary" href="#/sign-in">Secure Sign In</a>`}
    </div>
  </div>`;
}
function renderFooter() {
  $('#site-footer').innerHTML=`<div class="container"><div class="footer-grid">
    <div><div class="footer-brand">Coletti &amp; Co.</div><p class="small" style="max-width:360px;margin-top:12px;color:#adbec8">Independent evidence-intelligence and reconstruction. We show what the records support, where they conflict, what is missing, what can be reconciled, and what remains unresolved.</p></div>
    <div><div class="footer-title">Company</div><div class="footer-links"><a href="#/about">About</a><a href="#/services">Services</a><a href="#/how-it-works">How It Works</a><a href="#/pricing">Pricing &amp; Engagement</a></div></div>
    <div><div class="footer-title">Professionals</div><div class="footer-links"><a href="#/referral-partners">Referral Partners</a><a href="#/security">Security &amp; Privacy</a><a href="#/faq">FAQ</a><a href="#/contact">Contact</a></div></div>
    <div><div class="footer-title">Legal</div><div class="footer-links"><a href="#/privacy">Privacy Notice</a><a href="#/terms">Terms</a><a href="#/disclaimer">Professional Services Disclaimer</a><a href="#/sign-in">Client Portal</a></div></div>
  </div><div class="footer-bottom"><span>© ${new Date().getFullYear()} Coletti &amp; Co.</span><span>Not a law firm, accounting firm, or investigative agency.</span></div></div>`;
}

function publicHero(title, lede, eyebrow='Coletti & Co.') {
  return `<section class="public-page-hero"><div class="container content-narrow"><div class="eyebrow">${esc(eyebrow)}</div><h1>${title}</h1><p class="lede">${lede}</p></div></section>`;
}
function homePage() {
  return `<section class="hero"><div class="container hero-grid"><div><div class="eyebrow">Independent Evidence Intelligence</div><h1 class="display">Clarity you can trace back to the record.</h1><p class="lede">Coletti &amp; Co. transforms fragmented records into source-traceable, human-reviewed factual reconstructions—without telling you what to believe.</p><div class="hero-actions"><a class="btn btn-primary" href="#/contact">Request a Consultation</a><a class="btn btn-secondary" href="#/how-it-works">See How It Works</a></div><div class="hero-proof"><div class="proof-item"><strong>Source traceability</strong><br/>Every material proposition stays tied to its record origin.</div><div class="proof-item"><strong>Human review</strong><br/>Analysis does not become a client deliverable without review.</div><div class="proof-item"><strong>Controlled publication</strong><br/>Only approved outputs cross the publishing gate.</div></div></div>
  <aside class="hero-panel"><div class="eyebrow">Controlled Workflow</div><h3 style="font:700 26px Georgia,serif;margin:8px 0 20px">From secure intake to published reconstruction.</h3><div class="flow-stack">${['Secure Client Gateway','ColettiOS','Human Review / Approval','Publishing Gate','Client Portal'].map((x,i)=>`${i?'<div class="flow-arrow">↓</div>':''}<div class="flow-node"><strong>${x}</strong><span class="badge">${i===0?'Intake':i===4?'Delivery':'Controlled'}</span></div>`).join('')}</div></aside></div></section>
  <section class="section section-white"><div class="container"><div class="eyebrow">What we do</div><h2>Records and operations reconstruction for situations where the details matter.</h2><p class="lede">We organize source material, preserve provenance, surface conflicts, identify missing documentation, reconcile what can be reconciled, and separate record-supported facts from assertions and third-party conclusions.</p><div class="grid-3 mt-2">${(state.services.length?state.services.slice(0,3):[{name:'Diagnostic / Scoped Reconstruction',summary:'A bounded review of a defined record set and reconstruction question.'},{name:'Full Reconstruction Project',summary:'Deeper multi-source reconstruction for complex records or operations.'},{name:'Professional Handoff Package',summary:'Source-linked materials organized for a client-selected qualified professional.'}]).map((s,i)=>`<article class="card"><div class="icon">0${i+1}</div><h3>${esc(s.name)}</h3><p class="muted">${esc(s.summary)}</p><a class="small" href="#/services"><strong>Explore service →</strong></a></article>`).join('')}</div></div></section>
  <section class="section section-ivory"><div class="container grid-2"><div><div class="eyebrow">Evidence states</div><h2>Not every piece of information gets treated as a fact.</h2><p class="lede">ColettiOS preserves the distinction between what a record documents, what a person asserts, what a third party concludes, what conflicts, and what still needs verification.</p></div><div class="card card-flat"><div class="evidence-badges">${EVIDENCE_STATES.map(evidenceBadge).join('')}</div></div></div></section>
  <section class="section"><div class="container grid-2"><div class="card card-dark"><div class="eyebrow" style="color:#cfbd92">Professional boundary</div><h2>Independent reconstruction, not substituted professional judgment.</h2><p>Coletti &amp; Co. is not a law firm, accounting firm, or investigative agency. We do not make legal, accounting, tax, regulatory, evidentiary-admissibility, or licensed investigative determinations.</p><a class="btn btn-gold mt-1" href="#/disclaimer">Read the service boundary</a></div><div class="card"><div class="eyebrow">Need a clearer record?</div><h2>Start with a defined question and a controlled source set.</h2><p class="muted">Consultation and intake are handled through the Secure Client Gateway so sensitive matter details do not need to be sent through a public contact form.</p><a class="btn btn-primary mt-1" href="#/contact">Enter Secure Intake</a></div></div></section>`;
}
function servicesPage() {
  const services=state.services.length?state.services:[];
  return `${publicHero('Services built around the record.','Each engagement begins by defining the source universe, the reconstruction question, and the deliverable boundary.','Services')}
  <section class="section"><div class="container"><div class="grid-2">${services.map((s,i)=>`<article class="card"><div class="flex-between"><div class="icon">0${i+1}</div>${s.service_key==='recurring_review'?'<span class="badge badge-warning">Future option</span>':'<span class="badge badge-success">Service model</span>'}</div><h3 style="font-size:24px;font-family:Georgia,serif">${esc(s.name)}</h3><p>${esc(s.summary)}</p><div class="divider"></div><p class="small"><strong>Scope</strong><br/>${esc(s.scope_text || '')}</p><p class="small"><strong>Delivery</strong><br/>${esc(s.delivery_text || '')}</p></article>`).join('') || empty('Service definitions are being synchronized.')}</div><div class="notice notice-info mt-2">Engagement scope is confirmed before substantive work begins. A reconstruction engagement does not authorize Coletti &amp; Co. to act as your attorney, accountant, auditor, investigator, fiduciary, or other licensed professional.</div></div></section>`;
}
function howPage() {
  const steps=[['Secure Client Gateway','Secure sign-in, intake, contact information, engagement acknowledgments, document requests, and controlled uploads.'],['ColettiOS','Sources are registered, provenance is preserved, propositions are source-linked, and inconsistencies or gaps are surfaced for review.'],['Human Review / Approval','A human reviewer separates record content from inference, reviews contradictions and reconciliations, and checks professional-service boundaries.'],['Publishing Gate','Draft analysis remains internal. A report must be explicitly approved before a client-visible publication is created.'],['Client Portal','The client sees requests, status, messages, billing, and only the final reports that have actually been published.']];
  return `${publicHero('A controlled path from documents to deliverables.','The workflow is designed so raw uploads, internal review, and published client outputs are separate states.','How It Works')}<section class="section"><div class="container content-narrow"><div class="steps">${steps.map(([t,b])=>`<div class="step"><div><h3>${esc(t)}</h3><p class="muted mb-0">${esc(b)}</p></div></div>`).join('')}</div><div class="notice notice-warning mt-2"><strong>What the client does not see:</strong> internal hypotheses, private reviewer notes, internal scoring, unpublished draft narratives, or other material that has not crossed the publishing gate.</div></div></section>`;
}
function aboutPage() {
  return `${publicHero('Independent reconstruction. Human-reviewed conclusions.','Coletti & Co. exists to make complex records more intelligible without collapsing uncertainty into certainty.','About')}<section class="section section-white"><div class="container grid-2"><div><h2>We do not tell you what to believe.</h2><p class="lede">We show what the records support, where they conflict, what is missing, what can be reconciled, and what remains unresolved.</p></div><div class="card card-gold"><h3>Operating principle</h3><p>Source material, client assertions, third-party conclusions, reviewer decisions, and published findings remain distinguishable. Provenance is not discarded merely because a record has been summarized.</p></div></div></section><section class="section"><div class="container grid-3"><div class="card"><h3>Evidence-first</h3><p class="muted">Material statements should be traceable to identifiable sources and relationships.</p></div><div class="card"><h3>Human-reviewed</h3><p class="muted">Automation can organize and surface issues; release decisions remain human-controlled.</p></div><div class="card"><h3>Boundary-aware</h3><p class="muted">When a question requires a qualified professional determination, the reconstruction can identify the issue and route it for verification rather than invent the answer.</p></div></div></section>`;
}
function referralsPage() {
  return `${publicHero('Built to make professional handoffs cleaner.','Coletti & Co. can organize a fragmented record set before or alongside a client’s work with an attorney, CPA, consultant, licensed investigator, or other qualified professional.','Professional Referral Partners')}<section class="section"><div class="container grid-2"><div><h2>A cleaner record can make professional review more efficient.</h2><p class="lede">Referral-oriented engagements focus on chronology, provenance, source organization, inconsistencies, missing records, and unresolved verification questions—not on substituting for the professional’s judgment.</p><div class="notice notice-info mt-2">A referral relationship does not create a legal, accounting, investigative, fiduciary, or other professional relationship with Coletti &amp; Co., and we do not represent that a referring professional has endorsed any finding.</div></div><div class="card"><h3>Useful handoff components</h3><ul><li>Source manifest and immutable source identifiers</li><li>Source-linked factual propositions</li><li>Chronology and cross-record comparison</li><li>Contradiction and reconciliation summary</li><li>Missing-documentation register</li><li>Open verification/referral questions</li><li>Published reconstruction report and supporting references</li></ul><a class="btn btn-primary" href="#/contact">Discuss a referral workflow</a></div></div></section>`;
}
function pricingPage() {
  return `${publicHero('Scope first. Pricing second.','Coletti & Co. does not use a one-size-fits-all fee for reconstruction work. The quote follows a defined source universe, complexity level, timeline, and deliverable scope.','Pricing & Engagement')}<section class="section"><div class="container"><div class="grid-2">${state.pricing.map(p=>{const s=state.services.find(x=>x.service_key===p.service_key);return `<article class="card"><div class="flex-between"><h3>${esc(s?.name || p.label)}</h3>${p.billing_model==='NOT_YET_LAUNCHED'?'<span class="badge badge-warning">Not launched</span>':'<span class="badge">Custom quote</span>'}</div><p class="muted">${esc(p.public_note || '')}</p></article>`}).join('') || empty('Pricing configuration is being synchronized.')}</div><div class="card card-dark mt-2"><h2>Before work begins</h2><p>The engagement should identify the reconstruction question, expected source set, service boundary, client responsibilities, estimated fee or fee method, payment terms, and expected deliverables. No public price shown on this site overrides a signed engagement agreement.</p></div></div></section>`;
}
function securityPage() {
  return `${publicHero('Security-oriented by design, without inflated claims.','The operational website separates public browsing, authenticated client access, staff workspaces, and publication authority.','Security & Privacy')}<section class="section"><div class="container grid-2"><div class="card"><h3>Access isolation</h3><p class="muted">Authenticated data access is constrained by database row-level policies, case membership or staff assignment, and role-specific application navigation.</p></div><div class="card"><h3>Private file storage</h3><p class="muted">Client documents and published reports use private storage buckets. File access is tied to authenticated case access rather than public object URLs.</p></div><div class="card"><h3>Publishing separation</h3><p class="muted">Internal review material is not the same thing as a client-facing publication. Report release requires a separate publishing authority.</p></div><div class="card"><h3>Auditability</h3><p class="muted">Operational mutations are designed to create audit events while avoiding unnecessary duplication of sensitive free-text content into the audit record.</p></div><div class="card"><h3>Least-claim language</h3><p class="muted">We do not claim a certification, regulatory status, security standard, or legal compliance designation unless and until it has actually been established and documented.</p></div><div class="card"><h3>Integration roadmap</h3><p class="muted">Google Calendar, Gmail, and Drive workflows are anticipated, but future integrations must preserve the same authentication, authorization, audit, and case-isolation boundaries.</p></div></div></section>`;
}
function faqPage() {
  const faqs=[['Is Coletti & Co. a law firm?','No. Coletti & Co. is not a law firm and does not provide legal advice or legal representation.'],['Is this forensic accounting?','Coletti & Co. can reconstruct records and money-flow evidence, but it is not an accounting firm and does not issue accounting, tax, audit, valuation, or attestation opinions.'],['Are you a private investigator?','No. Coletti & Co. is not presented as an investigative agency. The service model is based on records supplied or lawfully authorized by the client and controlled reconstruction of those records.'],['What is a “Documented Fact”?','It is an evidence state used when the proposition is supported by the record set under review. It does not mean every possible outside fact has been independently verified.'],['Do clients see every internal note?','No. Private review notes, internal hypotheses or scores, and unpublished analysis stay outside the client portal.'],['Can my attorney or CPA receive the report?','A client may request a professional handoff package or authorized delivery, subject to engagement scope, authorization, and the publishing workflow.']];
  return `${publicHero('Frequently asked questions.','A short guide to the service model, boundaries, and workflow.','FAQ')}<section class="section"><div class="container content-narrow stack">${faqs.map(([q,a])=>`<div class="card card-flat"><h3>${esc(q)}</h3><p class="muted mb-0">${esc(a)}</p></div>`).join('')}</div></section>`;
}
function contactPage() {
  return `${publicHero('Start through the Secure Client Gateway.','Use the secure sign-in flow to begin intake. Do not put sensitive matter details into a public website form.','Request Consultation')}<section class="section"><div class="container grid-2"><div><h2>We start with enough information to scope the reconstruction—not your entire life story.</h2><p class="lede">Enter your email below. We’ll send a secure sign-in link. Once authenticated, you can complete intake and provide matter details inside the gateway.</p><div class="notice notice-warning mt-2">For security, this public page intentionally does not collect documents, account numbers, detailed allegations, medical information, or other sensitive case content.</div></div><div class="card"><form id="contact-signin-form"><div class="form-field"><label for="contact-email">Email address</label><input id="contact-email" name="email" type="email" autocomplete="email" required placeholder="you@example.com" /></div><button class="btn btn-primary mt-2" type="submit">Send Secure Sign-In Link</button><p class="micro mt-1">The link returns you to the Secure Client Gateway. Intake submission does not create an engagement until engagement terms are accepted.</p></form></div></div></section>`;
}
function legalPage(kind) {
  const content={
    disclaimer:['Professional Services Disclaimer',`Coletti & Co. is an independent evidence-intelligence and reconstruction firm. It is not a law firm, accounting firm, public accounting practice, audit firm, private investigative agency, or governmental authority. Its work does not constitute legal advice, accounting advice, tax advice, an audit or attestation, an evidentiary admissibility determination, a licensed investigation, or a guarantee that a court, regulator, insurer, financial institution, attorney, accountant, or other professional will adopt any conclusion.\n\nA reconstruction is limited by the records made available, the engagement scope, and the quality and completeness of those records. “Documented Fact” describes support within the reviewed record set; it is not a universal statement that no contrary evidence exists. Client assertions and third-party conclusions remain identified as such. Questions requiring a qualified professional determination may be marked for referral or verification.\n\nNo attorney-client, accountant-client, investigator-client, fiduciary, expert-witness, or similar licensed professional relationship is created by visiting this website or submitting intake.`],
    privacy:['Privacy Notice',`Coletti & Co. uses an authenticated client gateway for sensitive engagement information. Public pages are designed to minimize collection of sensitive case content. Authenticated portal data may include identity/contact information, intake content, engagement acknowledgments, uploaded documents, document requests, messages, scheduling requests, billing records, support requests, case-status events, and published reports.\n\nAccess to operational records is intended to be restricted by authenticated identity, role, case membership or assignment, and publication status. Private internal review notes are not intended for client-portal display.\n\nThis notice describes the current application design and is not a claim of a certification, statutory compliance status, or regulatory designation. Formal retention, deletion, incident-response, and jurisdiction-specific privacy terms should be finalized in controlled company policy before production launch to paying clients.`],
    terms:['Website & Portal Terms',`This website provides information about Coletti & Co. and access to an operational client gateway. Public content is informational and does not itself create an engagement. An engagement begins only when the required engagement terms and acknowledgments are accepted and Coletti & Co. confirms acceptance.\n\nUsers must access only accounts and cases for which they are authorized. Credentials and secure links should not be shared. Uploads should be records the user is authorized to provide. Coletti & Co. may decline, limit, pause, or terminate an engagement as provided in the applicable engagement terms.\n\nClient-facing reports are controlled publications. Drafts, internal notes, hypotheses, quality-control material, and unpublished review content are not client deliverables unless explicitly published or included in an executed engagement.`]
  }[kind];
  return `${publicHero(content[0],'Controlled legal and service-boundary language for the Coletti & Co. website.','Legal')}<section class="section"><div class="container content-narrow prose">${content[1].split('\n\n').map(p=>`<p>${esc(p)}</p>`).join('')}<div class="notice notice-info mt-2">This is operational website language and should remain subject to final company/legal review before external commercial launch.</div></div></section>`;
}
function signInPage() {
  if(state.user){go('/portal/home');return '<div class="loading">Redirecting…</div>'}
  return `<section class="auth-shell"><div class="auth-brand"><div class="eyebrow" style="color:#d2c094">Secure Client Gateway</div><h1>Coletti &amp; Co.</h1><p style="max-width:560px;color:#cbd8df">Authenticate before sending sensitive intake information, uploading records, viewing case status, messaging the firm, or retrieving a published report.</p></div><div class="auth-form"><div class="auth-card"><div class="eyebrow">Passwordless access</div><h2>Secure sign in</h2><p class="muted">We’ll send a time-limited sign-in link to your email.</p><form id="signin-form"><div class="form-field"><label for="signin-email">Email address</label><input id="signin-email" name="email" type="email" required autocomplete="email" /></div><button class="btn btn-primary mt-2" type="submit">Send Sign-In Link</button></form><div class="divider"></div><p class="micro">Authentication confirms identity. Access to any case remains separately limited by case membership, staff assignment, and role.</p></div></div></section>`;
}

const CLIENT_NAV=[['home','Overview'],['intake','Intake'],['profile','Identity & Contact'],['engagement','Engagement'],['uploads','Secure Uploads'],['requests','Document Requests'],['timeline','Case Status'],['messages','Messages'],['schedule','Meetings'],['billing','Invoices & Payments'],['reports','Published Reports'],['support','Support']];
const STAFF_NAV=[['home','Assigned Cases'],['intake','Intake Review'],['documents','Document Completeness'],['evidence','Evidence & Provenance'],['contradictions','Contradictions / Reconciliation'],['narratives','Review Narratives'],['requests','Client Requests & Deadlines'],['notes','Case Notes'],['qa','QA Checklist'],['publishing','Publishing Handoff']];
const ADMIN_NAV=[['home','Command Center'],['users','Users & Roles'],['assignments','Case Assignment'],['audit','Audit Trail'],['access','Access Controls'],['services','Services & Pricing'],['templates','Templates'],['publications','Publication Controls'],['analytics','Analytics / KPIs'],['billing','Billing Overview'],['referrals','Referral Pipeline'],['capacity','Capacity / Workload'],['health','System Health'],['security','Security Alerts'],['backups','Backup / Recovery'],['settings','Settings']];
function caseSelector() {
  if(!state.caseIds.length) return '<span class="badge badge-neutral">No active case access</span>';
  return `<select id="case-selector" aria-label="Active case" style="width:auto;min-width:190px">${state.caseIds.map(id=>`<option value="${esc(id)}" ${id===state.activeCase?'selected':''}>${esc(id)}</option>`).join('')}</select>`;
}
function workspaceLayout(kind, active, title, subtitle, body) {
  const nav=kind==='portal'?CLIENT_NAV:kind==='workspace'?STAFF_NAV:ADMIN_NAV;
  const base=kind==='portal'?'portal':kind==='workspace'?'workspace':'admin';
  const groups=kind==='admin'?[['Administration',nav]]:kind==='workspace'?[['Case Operations',nav]]:[['Client Portal',nav]];
  return `<div class="workspace-shell ${kind==='portal'?'client-shell':''}"><aside class="workspace-sidebar"><div class="workspace-title">${kind==='portal'?'Client Portal':kind==='workspace'?'Operations Workspace':'Owner / Admin'}</div><div class="workspace-role">${esc(titleCase(state.profile?.role))} · ${esc(state.profile?.display_name || state.user?.email)}</div>${groups.map(([label,items])=>`<div class="side-group"><div class="side-label">${label}</div>${items.map(([id,l])=>`<a class="side-link ${active===id?'active':''}" href="#/${base}/${id}">${esc(l)}</a>`).join('')}</div>`).join('')}</aside><section class="workspace-main"><div class="workspace-topbar"><div><h1>${esc(title)}</h1><p class="muted mb-0">${esc(subtitle)}</p></div><div class="workspace-actions">${kind!=='admin'?caseSelector():''}<button class="btn btn-ghost btn-sm" data-action="signout">Sign out</button></div></div>${body}</section></div>`;
}
function noCase() { return panel('No case workspace yet',empty('Complete intake first. Case access appears after the engagement is accepted and a case is established in the controlled registry.'),'Your portal remains available for intake, profile, and support.'); }

async function portalPage(view) {
  if(!requireAuth()) return '';
  if(STAFF_ROLES.includes(state.profile?.role) && view==='home'){ go('/workspace/home'); return ''; }
  const c=state.activeCase;
  if(view==='home'){
    const [reqs,status,invoices,reports]=c?await Promise.all([q('document_requests','*',x=>x.eq('case_id',c).order('created_at',{ascending:false})),q('case_status_events','*',x=>x.eq('case_id',c).order('occurred_at',{ascending:false}).limit(6)),q('invoices','*',x=>x.eq('case_id',c).order('created_at',{ascending:false})),q('published_reports','*',x=>x.eq('case_id',c).is('revoked_at',null).order('published_at',{ascending:false}))]):[[],[],[],[]];
    const body=`${!c?noCase():`<div class="grid-4"><div class="card metric"><div class="metric-value">${reqs.filter(x=>!['SATISFIED','WAIVED'].includes(x.status)).length}</div><div class="metric-label">Open requests</div></div><div class="card metric"><div class="metric-value">${status[0]?esc(status[0].stage):'—'}</div><div class="metric-label">Current stage</div></div><div class="card metric"><div class="metric-value">${invoices.filter(x=>x.status==='OPEN'||x.status==='PAST_DUE').length}</div><div class="metric-label">Open invoices</div></div><div class="card metric"><div class="metric-value">${reports.length}</div><div class="metric-label">Published reports</div></div></div>${panel('Recent case activity',status.length?`<div class="timeline">${status.map(s=>`<div class="timeline-item"><strong>${esc(s.title)}</strong><div class="small muted">${fmtDate(s.occurred_at)} · ${esc(s.stage)}</div>${s.description?`<div class="small mt-1">${esc(s.description)}</div>`:''}</div>`).join('')}</div>`:empty('No client-visible status events have been published yet.'),'Only client-visible timeline events appear here.')}${panel('Document requests',table(reqs.slice(0,5),[{label:'Request',key:'title'},{label:'Due',render:r=>fmtDate(r.due_date)},{label:'Status',render:r=>badge(r.status)}]),'Items requested by your Coletti & Co. team.')}`}`;
    return workspaceLayout('portal','home','Your workspace',c?`Authorized case: ${c}`:'Secure gateway',body);
  }
  if(view==='profile') return workspaceLayout('portal','profile','Identity & contact','Keep your client contact information current.',panel('Profile',`<form id="profile-form"><div class="form-grid"><div class="form-field"><label>Display name</label><input name="display_name" value="${esc(state.profile?.display_name||'')}" required /></div><div class="form-field"><label>Email</label><input value="${esc(state.user.email||'')}" disabled /></div><div class="form-field"><label>Phone</label><input name="phone" value="${esc(state.profile?.phone||'')}" /></div><div class="form-field"><label>Organization</label><input name="organization_name" value="${esc(state.profile?.organization_name||'')}" /></div></div><div class="form-actions"><button class="btn btn-primary">Save profile</button></div></form>`,'Identity is authenticated separately from case authorization.'));
  if(view==='intake'){
    const rows=await q('intake_submissions','*',x=>x.eq('user_id',state.user.id).order('created_at',{ascending:false}));
    const form=`<form id="intake-form"><div class="form-grid"><div class="form-field"><label>Service requested</label><select name="service_requested" required><option value="">Choose…</option>${state.services.filter(s=>s.service_key!=='recurring_review').map(s=>`<option value="${esc(s.service_key)}">${esc(s.name)}</option>`).join('')}</select></div><div class="form-field"><label>Referral source (optional)</label><input name="referral_source" placeholder="Attorney, CPA, colleague, web search…" /></div><div class="form-field full"><label>What record problem needs to be reconstructed?</label><textarea name="matter_summary" required placeholder="Describe the reconstruction question and the kinds of records involved. Do not speculate beyond what you need to scope the work."></textarea></div></div><div class="checkbox-row mt-1"><input type="checkbox" id="intake-truth" required /><label for="intake-truth">I understand this is an intake request, not legal/accounting/investigative advice and not yet an accepted engagement.</label></div><div class="form-actions"><button class="btn btn-primary">Submit intake</button></div></form>`;
    return workspaceLayout('portal','intake','Intake','Define the reconstruction question before uploading the full source set.',panel('New intake',form,'Sensitive intake content is available only inside the authenticated gateway.')+panel('Prior intake submissions',table(rows,[{label:'Submitted',render:r=>fmtDate(r.submitted_at||r.created_at)},{label:'Service',render:r=>esc(titleCase(r.service_requested))},{label:'Status',render:r=>badge(r.status)},{label:'Case',render:r=>esc(r.case_id||'Not assigned')}])));
  }
  if(view==='engagement'){
    const rows=await q('engagement_acceptances','*',x=>x.eq('user_id',state.user.id).order('created_at',{ascending:false}));
    const latestIntake=(await q('intake_submissions','id,status',x=>x.eq('user_id',state.user.id).order('created_at',{ascending:false}).limit(1)))[0];
    const form=`<form id="engagement-form"><input type="hidden" name="intake_id" value="${esc(latestIntake?.id||'')}" /><div class="notice notice-warning">Electronic acknowledgment placeholder: the final controlled engagement agreement and any third-party e-sign certificate must be substituted before commercial launch. This screen records an application acknowledgment only.</div><div class="form-field mt-2"><label>Signature name</label><input name="signature_name" required value="${esc(state.profile?.display_name||'')}" /></div><div class="checkbox-row mt-1"><input type="checkbox" id="engage-ack" required /><label for="engage-ack">I acknowledge the service boundary and understand an engagement is not accepted until Coletti &amp; Co. confirms it.</label></div><div class="form-actions"><button class="btn btn-primary" ${!latestIntake?'disabled':''}>Record acknowledgment</button></div></form>`;
    return workspaceLayout('portal','engagement','Engagement & acknowledgments','Controlled acceptance records and e-sign integration placeholder.',panel('Engagement acknowledgment',form,latestIntake?'Latest intake found.':'Submit intake before recording an engagement acknowledgment.')+panel('Acknowledgment history',table(rows,[{label:'Document',key:'document_key'},{label:'Version',key:'document_version'},{label:'Accepted',render:r=>badge(r.accepted?'accepted':'not accepted')},{label:'Date',render:r=>fmtDate(r.accepted_at)}])));
  }
  if(view==='uploads'){
    const rows=await q('upload_records','*',x=>c?x.eq('case_id',c).order('created_at',{ascending:false}):x.eq('uploaded_by',state.user.id).order('created_at',{ascending:false}));
    const intakes=await q('intake_submissions','id,status,submitted_at',x=>x.eq('user_id',state.user.id).order('created_at',{ascending:false}));
    const form=`<form id="upload-form"><div class="form-grid"><div class="form-field"><label>Upload destination</label><select name="destination">${c?`<option value="case">Active case — ${esc(c)}</option>`:''}${intakes.length?`<option value="intake">Latest intake</option>`:''}</select></div><div class="form-field"><label>File</label><input name="file" type="file" required accept=".pdf,.png,.jpg,.jpeg,.txt,.csv,.xlsx,.docx,.eml" /></div></div><div class="notice notice-info mt-1">Uploads enter private storage. An uploaded file is not automatically promoted into a ColettiOS Source ID; ingestion and source registration remain controlled workflow steps.</div><div class="form-actions"><button class="btn btn-primary">Upload securely</button></div></form>`;
    return workspaceLayout('portal','uploads','Secure uploads','Private file storage tied to intake or case authorization.',panel('Upload records',form)+panel('Upload history',table(rows,[{label:'File',key:'original_filename'},{label:'Received',render:r=>fmtDate(r.created_at)},{label:'Source ID',render:r=>esc(r.source_id||'Pending ingestion')},{label:'Status',render:r=>badge(r.status)}])));
  }
  if(!c && !['support'].includes(view)) return workspaceLayout('portal',view,'Client Portal','A case has not been established yet.',noCase());
  if(view==='requests'){
    const rows=await q('document_requests','*',x=>x.eq('case_id',c).order('created_at',{ascending:false}));
    return workspaceLayout('portal','requests','Document requests',c,panel('Requested records',table(rows,[{label:'Request',render:r=>`<strong>${esc(r.title)}</strong>${r.description?`<div class="micro">${esc(r.description)}</div>`:''}`},{label:'Due',render:r=>fmtDate(r.due_date)},{label:'Status',render:r=>badge(r.status)}]),'Only client-visible requests appear in this portal.'));
  }
  if(view==='timeline'){
    const rows=await q('case_status_events','*',x=>x.eq('case_id',c).order('occurred_at',{ascending:false}));
    return workspaceLayout('portal','timeline','Case status & timeline',c,panel('Published status',rows.length?`<div class="timeline">${rows.map(r=>`<div class="timeline-item"><strong>${esc(r.title)}</strong><div class="small muted">${fmtDate(r.occurred_at)} · ${esc(r.stage)}</div>${r.description?`<p class="small mt-1">${esc(r.description)}</p>`:''}</div>`).join('')}</div>`:empty('No client-visible status events have been published yet.'),'Internal operational notes and draft work do not appear here.'));
  }
  if(view==='messages'){
    const rows=await q('portal_messages','*',x=>x.eq('case_id',c).eq('thread_type','CLIENT').order('created_at'));
    const body=`<div class="stack">${rows.length?rows.map(r=>`<div class="card card-flat"><div class="flex-between"><strong>${r.sender_id===state.user.id?'You':'Coletti & Co.'}</strong><span class="micro">${fmtDate(r.created_at)}</span></div><p class="small mb-0 mt-1">${esc(r.body)}</p></div>`).join(''):empty('No messages yet.')}</div><form id="message-form" class="mt-2"><div class="form-field"><label>New message</label><textarea name="body" required></textarea></div><div class="form-actions"><button class="btn btn-primary">Send message</button></div></form>`;
    return workspaceLayout('portal','messages','Messages',c,panel('Case messaging',body,'Client thread only. Internal staff notes are separate and are not portal-visible.'));
  }
  if(view==='schedule'){
    const rows=await q('meeting_requests','*',x=>x.eq('case_id',c).order('created_at',{ascending:false}));
    const form=`<form id="meeting-form"><div class="form-grid"><div class="form-field"><label>Topic</label><input name="topic" required /></div><div class="form-field"><label>Preferred date/time</label><input name="slot" type="datetime-local" required /></div><div class="form-field full"><label>Notes</label><textarea name="notes"></textarea></div></div><div class="form-actions"><button class="btn btn-primary">Request meeting</button></div></form>`;
    return workspaceLayout('portal','schedule','Meeting scheduling',c,panel('Request a meeting',form,'Google Calendar integration is planned; current requests enter the controlled scheduling queue.')+panel('Meeting requests',table(rows,[{label:'Topic',key:'topic'},{label:'Requested',render:r=>fmtDate(r.created_at)},{label:'Status',render:r=>badge(r.status)}])));
  }
  if(view==='billing'){
    const invoices=await q('invoices','*',x=>x.eq('case_id',c).order('created_at',{ascending:false}));
    return workspaceLayout('portal','billing','Invoices & payments',c,panel('Billing',table(invoices,[{label:'Invoice',key:'invoice_number'},{label:'Amount',render:r=>fmtMoney(r.amount_cents)},{label:'Due',render:r=>fmtDate(r.due_date)},{label:'Status',render:r=>badge(r.status)},{label:'Payment',render:r=>r.payment_url?`<a class="btn btn-primary btn-sm" rel="noopener" target="_blank" href="${esc(safeHref(r.payment_url))}">Pay securely</a>`:'<span class="micro">Payment link not issued</span>'}]),'Payment-provider links appear only when an invoice has an authorized payment URL.'));
  }
  if(view==='reports'){
    const rows=await q('published_reports','*',x=>x.eq('case_id',c).is('revoked_at',null).eq('client_visible',true).order('published_at',{ascending:false}));
    return workspaceLayout('portal','reports','Published reports',c,panel('Final published deliverables',table(rows,[{label:'Report',render:r=>`<strong>${esc(r.title)}</strong><div class="micro">${esc(r.report_type)} · v${r.version}</div>`},{label:'Published',render:r=>fmtDate(r.published_at)},{label:'Download',render:r=>`<button class="btn btn-primary btn-sm" data-action="download-report" data-path="${esc(r.storage_path)}">Secure download</button>`}]),'Only reports that crossed the publishing gate are shown. Drafts and internal review material are excluded.'));
  }
  if(view==='support'){
    const rows=await q('support_tickets','*',x=>x.eq('user_id',state.user.id).order('created_at',{ascending:false}));
    const form=`<form id="support-form"><div class="form-grid"><div class="form-field"><label>Category</label><select name="category"><option>Portal access</option><option>Upload issue</option><option>Billing</option><option>Case question</option><option>Other</option></select></div><div class="form-field"><label>Subject</label><input name="subject" required /></div><div class="form-field full"><label>Message</label><textarea name="body" required></textarea></div></div><div class="form-actions"><button class="btn btn-primary">Open support request</button></div></form>`;
    return workspaceLayout('portal','support','Support','Portal, upload, billing, or workflow support.',panel('New support request',form)+panel('Support history',table(rows,[{label:'Subject',key:'subject'},{label:'Opened',render:r=>fmtDate(r.created_at)},{label:'Status',render:r=>badge(r.status)}])));
  }
  return '';
}

async function staffPage(view) {
  if(!requireStaff()) return '';
  const c=state.activeCase;
  if(view==='home'){
    const assigns=await q('case_assignments','*',x=>x.eq('staff_user_id',state.user.id).eq('active',true).order('assigned_at',{ascending:false}));
    const openItems=c?await q('evidence_work_items','*',x=>x.eq('case_id',c).in('status',['OPEN','IN_REVIEW']).order('created_at',{ascending:false}).limit(8)):[];
    return workspaceLayout('workspace','home','Assigned cases','Operational workspace; client publication is a separate controlled state.',panel('Your assignments',table(assigns,[{label:'Case',key:'case_id'},{label:'Role',render:r=>badge(r.assignment_role)},{label:'Assigned',render:r=>fmtDate(r.assigned_at)}]))+(c?panel('Open review work',table(openItems,[{label:'Queue',render:r=>badge(r.queue_type)},{label:'Summary',key:'summary'},{label:'State',render:r=>r.evidence_state?evidenceBadge(r.evidence_state):'—'},{label:'Status',render:r=>badge(r.status)}]),c):''));
  }
  if(view==='intake'){
    const rows=await q('intake_submissions','*',x=>x.order('created_at',{ascending:false}).limit(100));
    return workspaceLayout('workspace','intake','Intake review','Review incoming engagements without converting intake assertions into findings.',panel('Intake queue',table(rows,[{label:'Received',render:r=>fmtDate(r.created_at)},{label:'Service',render:r=>esc(titleCase(r.service_requested))},{label:'Summary',render:r=>`<span class="small">${esc((r.matter_summary||'').slice(0,180))}</span>`},{label:'Status',render:r=>badge(r.status)},{label:'Action',render:r=>`<select data-action="intake-status" data-id="${r.id}"><option>${r.status}</option>${['IN_REVIEW','ACCEPTED','DECLINED'].filter(x=>x!==r.status).map(x=>`<option>${x}</option>`).join('')}</select>`}]),'Client statements in intake remain client assertions unless separately supported by records.'));
  }
  if(!c) return workspaceLayout('workspace',view,'Operations Workspace','Choose an assigned case to continue.',noCase());
  if(view==='documents'){
    const [requests,uploads]=await Promise.all([q('document_requests','*',x=>x.eq('case_id',c).order('created_at',{ascending:false})),q('upload_records','*',x=>x.eq('case_id',c).order('created_at',{ascending:false}))]);
    return workspaceLayout('workspace','documents','Document completeness',c,panel('Requests',table(requests,[{label:'Request',key:'title'},{label:'Due',render:r=>fmtDate(r.due_date)},{label:'Status',render:r=>badge(r.status)}]))+panel('Received uploads',table(uploads,[{label:'File',key:'original_filename'},{label:'Source ID',render:r=>esc(r.source_id||'Not ingested')},{label:'Status',render:r=>badge(r.status)},{label:'Hash',render:r=>`<span class="micro">${esc(r.sha256?r.sha256.slice(0,16)+'…':'Pending')}</span>`}]),'An upload is not a Source ID until controlled ingestion/registration occurs.'));
  }
  if(view==='evidence' || view==='contradictions'){
    const filter=view==='contradictions'?['CONTRADICTION','RECONCILIATION']:null;
    const rows=await q('evidence_work_items','*',x=>{let y=x.eq('case_id',c).order('created_at',{ascending:false});return filter?y.in('queue_type',filter):y;});
    const form=`<form id="evidence-form"><input type="hidden" name="view" value="${view}" /><div class="form-grid"><div class="form-field"><label>Queue type</label><select name="queue_type">${['SOURCE_REVIEW','EVIDENCE_STATE','CONTRADICTION','RECONCILIATION','MISSING_DOCUMENTATION','REFERRAL'].map(x=>`<option ${view==='contradictions'&&['CONTRADICTION','RECONCILIATION'].includes(x)?'selected':''}>${x}</option>`).join('')}</select></div><div class="form-field"><label>Evidence state</label><select name="evidence_state"><option value="">Not assigned</option>${EVIDENCE_STATES.map(x=>`<option>${x}</option>`).join('')}</select></div><div class="form-field"><label>Source ID (optional)</label><input name="source_id" placeholder="SRB-001" /></div><div class="form-field"><label>Proposition UUID (optional)</label><input name="proposition_id" /></div><div class="form-field full"><label>Summary</label><textarea name="summary" required></textarea></div><div class="form-field full"><label>Private internal notes</label><textarea name="internal_notes"></textarea></div></div><div class="form-actions"><button class="btn btn-primary">Add work item</button></div></form>`;
    return workspaceLayout('workspace',view,view==='contradictions'?'Contradiction & reconciliation queue':'Evidence & provenance review',c,panel('New internal work item',form,'Internal notes are never exposed by client portal policies.')+panel('Queue',table(rows,[{label:'Type',render:r=>badge(r.queue_type)},{label:'Source',render:r=>esc(r.source_id||'—')},{label:'Summary',key:'summary'},{label:'Evidence state',render:r=>r.evidence_state?evidenceBadge(r.evidence_state):'—'},{label:'Status',render:r=>badge(r.status)}],true)));
  }
  if(view==='narratives'){
    const rows=await q('review_narratives','*',x=>x.eq('case_id',c).order('created_at',{ascending:false}));
    const form=`<form id="narrative-form"><div class="form-field"><label>Review narrative</label><textarea name="narrative" required placeholder="Source-aware reviewer narrative. Keep source content separate from reviewer conclusion."></textarea></div><div class="form-field mt-1"><label>Status</label><select name="status"><option>DRAFT</option><option>READY_FOR_QA</option><option>FINAL_INTERNAL</option></select></div><div class="form-actions"><button class="btn btn-primary">Save narrative</button></div></form>`;
    return workspaceLayout('workspace','narratives','Review narratives',c,panel('New narrative',form,'Private review content; not a client-facing finding.')+panel('Narratives',table(rows,[{label:'Created',render:r=>fmtDate(r.created_at)},{label:'Narrative',render:r=>esc((r.narrative||'').slice(0,220))},{label:'Status',render:r=>badge(r.status)}])));
  }
  if(view==='requests'){
    const rows=await q('document_requests','*',x=>x.eq('case_id',c).order('created_at',{ascending:false}));
    const form=`<form id="document-request-form"><div class="form-grid"><div class="form-field"><label>Request title</label><input name="title" required /></div><div class="form-field"><label>Due date</label><input name="due_date" type="date" /></div><div class="form-field full"><label>Description</label><textarea name="description"></textarea></div></div><div class="checkbox-row mt-1"><input type="checkbox" name="client_visible" id="req-visible" checked /><label for="req-visible">Visible to client</label></div><div class="form-actions"><button class="btn btn-primary">Create request</button></div></form>`;
    return workspaceLayout('workspace','requests','Client requests & deadlines',c,panel('New request',form)+panel('Request register',table(rows,[{label:'Request',key:'title'},{label:'Due',render:r=>fmtDate(r.due_date)},{label:'Client visible',render:r=>badge(r.client_visible?'yes':'internal')},{label:'Status',render:r=>badge(r.status)}])));
  }
  if(view==='notes'){
    const rows=await q('case_notes','*',x=>x.eq('case_id',c).order('created_at',{ascending:false}));
    const form=`<form id="case-note-form"><div class="form-field"><label>Note type</label><select name="note_type"><option>GENERAL</option><option>CLIENT_CONTACT</option><option>REVIEW</option><option>DEADLINE</option><option>QA</option></select></div><div class="form-field mt-1"><label>Private case note</label><textarea name="body" required></textarea></div><div class="form-actions"><button class="btn btn-primary">Save note</button></div></form>`;
    return workspaceLayout('workspace','notes','Case notes',c,panel('Private note',form,'Case notes are internal-only under the portal access policy.')+panel('Note history',table(rows,[{label:'Date',render:r=>fmtDate(r.created_at)},{label:'Type',render:r=>badge(r.note_type)},{label:'Note',render:r=>esc((r.body||'').slice(0,240))}])));
  }
  if(view==='qa'){
    const rows=await q('qa_checklists','*',x=>x.eq('case_id',c).order('created_at'));
    const form=`<form id="qa-form"><div class="form-grid"><div class="form-field"><label>Item key</label><input name="item_key" required placeholder="source-lineage-reviewed" /></div><div class="form-field"><label>Status</label><select name="status"><option>PENDING</option><option>PASS</option><option>FAIL</option><option>NOT_APPLICABLE</option></select></div><div class="form-field full"><label>Checklist item</label><input name="label" required /></div><div class="form-field full"><label>Notes</label><textarea name="notes"></textarea></div></div><div class="form-actions"><button class="btn btn-primary">Save QA item</button></div></form>`;
    return workspaceLayout('workspace','qa','QA checklist',c,panel('Add QA control',form)+panel('Checklist',table(rows,[{label:'Control',key:'label'},{label:'Status',render:r=>badge(r.status)},{label:'Completed',render:r=>fmtDate(r.completed_at)},{label:'Notes',key:'notes'}])));
  }
  if(view==='publishing'){
    const rows=await q('publication_handoffs','*',x=>x.eq('case_id',c).order('created_at',{ascending:false}));
    const form=`<form id="handoff-form"><div class="form-grid"><div class="form-field"><label>Registry report UUID (optional)</label><input name="registry_report_id" /></div><div class="form-field"><label>Status</label><select name="status"><option>DRAFT</option><option>READY_FOR_REVIEW</option></select></div><div class="form-field full"><label>Private handoff notes</label><textarea name="internal_notes"></textarea></div></div><div class="form-actions"><button class="btn btn-primary">Create handoff</button></div></form>`;
    return workspaceLayout('workspace','publishing','Publishing handoff',c,panel('Prepare handoff',form,'Employees prepare and route publication. Client visibility does not occur here.')+panel('Handoff history',table(rows,[{label:'Created',render:r=>fmtDate(r.created_at)},{label:'Report',render:r=>esc(r.registry_report_id||'Not linked')},{label:'Status',render:r=>badge(r.status)}])));
  }
  return '';
}

async function adminPage(view) {
  if(!requireAdmin()) return '';
  if(view==='home'){
    const [intakes, invoices, tickets, alerts, handoffs] = await Promise.all([
      count('intake_submissions',x=>x.in('status',['SUBMITTED','IN_REVIEW'])), count('invoices',x=>x.in('status',['OPEN','PAST_DUE'])), count('support_tickets',x=>x.in('status',['OPEN','IN_PROGRESS','WAITING_ON_CLIENT'])), count('security_alerts',x=>x.eq('status','OPEN')), count('publication_handoffs',x=>x.in('status',['READY_FOR_REVIEW','APPROVED']))
    ]);
    const body=`<div class="grid-4"><div class="card metric"><div class="metric-value">${intakes}</div><div class="metric-label">Intakes awaiting review</div></div><div class="card metric"><div class="metric-value">${handoffs}</div><div class="metric-label">Publication queue</div></div><div class="card metric"><div class="metric-value">${invoices}</div><div class="metric-label">Open invoices</div></div><div class="card metric"><div class="metric-value">${alerts}</div><div class="metric-label">Open security alerts</div></div></div>${panel('Control plane',`<div class="grid-3"><a class="card card-flat" href="#/admin/users"><h3>Users & roles</h3><p class="muted small">Role administration and access state.</p></a><a class="card card-flat" href="#/admin/audit"><h3>Audit trail</h3><p class="muted small">Operational mutation history.</p></a><a class="card card-flat" href="#/admin/health"><h3>System health</h3><p class="muted small">Operational, security, and backup state.</p></a></div>`,'Owner/admin controls remain separate from employee case-work screens.')}`;
    return workspaceLayout('admin','home','Command Center','Full-access operating view for Coletti & Co.',body);
  }
  if(view==='users'){
    const rows=await q('profiles','*',x=>x.order('created_at',{ascending:false}));
    return workspaceLayout('admin','users','Users & roles','Roles are authorization-controlled; profile role is a read mirror, not the RLS authority.',panel('Accounts',table(rows,[{label:'User',render:r=>`<strong>${esc(r.display_name||'Unnamed')}</strong><div class="micro">${esc(r.id)}</div>`},{label:'Status',render:r=>badge(r.status)},{label:'Role',render:r=>`<select data-role-user="${r.id}">${['owner','admin','analyst','reviewer','client','read_only'].map(x=>`<option ${x===r.role?'selected':''}>${x}</option>`).join('')}</select>`},{label:'Action',render:r=>`<button class="btn btn-primary btn-sm" data-action="save-role" data-user="${r.id}">Save role</button>`}]),'Role changes use a security-definer RPC that re-checks admin authorization and prevents demotion of the last active owner.'));
  }
  if(view==='assignments'){
    const [rows,users]=await Promise.all([q('case_assignments','*',x=>x.order('assigned_at',{ascending:false})),q('profiles','id,display_name,role',x=>x.in('role',['owner','admin','analyst','reviewer']))]);
    const form=`<form id="assignment-form"><div class="form-grid"><div class="form-field"><label>Case ID</label><input name="case_id" required placeholder="REC-260906-01" /></div><div class="form-field"><label>Staff member</label><select name="staff_user_id" required>${users.map(u=>`<option value="${u.id}">${esc(u.display_name||u.id)} · ${esc(u.role)}</option>`).join('')}</select></div><div class="form-field"><label>Assignment role</label><select name="assignment_role"><option>analyst</option><option>reviewer</option><option>case_manager</option></select></div></div><div class="form-actions"><button class="btn btn-primary">Assign case</button></div></form>`;
    return workspaceLayout('admin','assignments','Case assignment','Case IDs must already exist in the controlled ColettiOS registry.',panel('New assignment',form)+panel('Assignments',table(rows,[{label:'Case',key:'case_id'},{label:'Staff UUID',key:'staff_user_id'},{label:'Role',render:r=>badge(r.assignment_role)},{label:'Active',render:r=>badge(r.active?'active':'inactive')}])));
  }
  if(view==='audit'){
    const rows=await q('audit_events','*',x=>x.order('created_at',{ascending:false}).limit(250));
    return workspaceLayout('admin','audit','Audit trail','Application-level mutation log with sensitive free-text fields redacted from audit snapshots.',panel('Recent events',table(rows,[{label:'Time',render:r=>fmtDate(r.created_at)},{label:'Actor role',render:r=>badge(r.actor_role||'system')},{label:'Action',render:r=>badge(r.action)},{label:'Object',render:r=>`${esc(r.object_type)}<div class="micro">${esc(r.object_id||'')}</div>`},{label:'Case',key:'case_id'}],true)));
  }
  if(view==='access'){
    return workspaceLayout('admin','access','Access controls','Human-readable view of the operating authorization model.',`<div class="grid-2"><div class="card"><h3>Client</h3><p class="muted">Own profile, own intake, accepted acknowledgments, authorized cases, client-visible requests/status, client messages, own invoices, support, and published reports only.</p></div><div class="card"><h3>Employee</h3><p class="muted">Only assigned cases; evidence/review queues, internal notes, QA and publishing handoff. No owner-level configuration unless separately authorized.</p></div><div class="card"><h3>Reviewer</h3><p class="muted">Assigned review plus publishing authority for assigned cases. Human approval remains a distinct workflow action.</p></div><div class="card"><h3>Owner / Admin</h3><p class="muted">User roles, assignments, configuration, billing overview, referrals, audit, publications, analytics and operating health.</p></div></div><div class="notice notice-info mt-2">Authorization truth is stored outside user-editable metadata. Browser access uses a public publishable key; database RLS remains the enforcement boundary for user data.</div>`);
  }
  if(view==='services'){
    const [services,pricing]=await Promise.all([q('service_definitions','*',x=>x.order('sort_order')),q('pricing_config','*',x=>x.order('created_at'))]);
    const form=`<form id="service-form"><div class="form-grid"><div class="form-field"><label>Service key</label><input name="service_key" required /></div><div class="form-field"><label>Name</label><input name="name" required /></div><div class="form-field full"><label>Summary</label><textarea name="summary" required></textarea></div><div class="form-field full"><label>Scope</label><textarea name="scope_text"></textarea></div><div class="form-field full"><label>Delivery</label><textarea name="delivery_text"></textarea></div></div><div class="form-actions"><button class="btn btn-primary">Add service</button></div></form>`;
    return workspaceLayout('admin','services','Services & pricing','Public service catalog and engagement pricing configuration.',panel('Service definitions',table(services,[{label:'Service',render:r=>`<strong>${esc(r.name)}</strong><div class="micro">${esc(r.service_key)}</div>`},{label:'Summary',render:r=>esc((r.summary||'').slice(0,180))},{label:'Public',render:r=>badge(r.public_visible?'yes':'no')},{label:'Active',render:r=>badge(r.active?'active':'inactive')}]))+panel('Add service',form)+panel('Pricing configuration',table(pricing,[{label:'Service',key:'service_key'},{label:'Label',key:'label'},{label:'Model',render:r=>badge(r.billing_model)},{label:'Public note',key:'public_note'}])));
  }
  if(view==='templates'){
    const rows=await q('template_catalog','*',x=>x.order('updated_at',{ascending:false}));
    const form=`<form id="template-form"><div class="form-grid"><div class="form-field"><label>Template key</label><input name="template_key" required /></div><div class="form-field"><label>Name</label><input name="name" required /></div><div class="form-field"><label>Type</label><input name="template_type" required placeholder="report, engagement, request…" /></div><div class="form-field"><label>Version</label><input name="version" required /></div><div class="form-field full"><label>Description</label><textarea name="description"></textarea></div></div><div class="form-actions"><button class="btn btn-primary">Add template</button></div></form>`;
    return workspaceLayout('admin','templates','Templates','Controlled template catalog; template content can later be attached to authoritative artifact storage.',panel('Catalog',table(rows,[{label:'Template',render:r=>`<strong>${esc(r.name)}</strong><div class="micro">${esc(r.template_key)}</div>`},{label:'Type',key:'template_type'},{label:'Version',key:'version'},{label:'Status',render:r=>badge(r.status)}]))+panel('Add template record',form));
  }
  if(view==='publications'){
    const [handoffs,reports]=await Promise.all([q('publication_handoffs','*',x=>x.order('created_at',{ascending:false}).limit(100)),q('published_reports','*',x=>x.order('published_at',{ascending:false}).limit(100))]);
    const form=`<form id="publish-report-form"><div class="form-grid"><div class="form-field"><label>Case ID</label><input name="case_id" required placeholder="REC-260906-01" /></div><div class="form-field"><label>Report title</label><input name="title" required /></div><div class="form-field"><label>Report type</label><select name="report_type"><option>Records Reconstruction Report</option><option>Operations Reconstruction Report</option><option>Findings Report</option><option>Professional Handoff Package</option></select></div><div class="form-field"><label>Version</label><input type="number" name="version" min="1" value="1" required /></div><div class="form-field full"><label>Final approved PDF</label><input type="file" name="file" accept="application/pdf" required /></div></div><div class="notice notice-warning mt-1">Use only for a final report that has completed human review and approval. Uploading here creates a client-visible published-report record if authorization succeeds.</div><div class="form-actions"><button class="btn btn-primary">Publish approved report</button></div></form>`;
    return workspaceLayout('admin','publications','Publication controls','Explicit publishing gate between internal review and client delivery.',panel('Publish approved report',form)+panel('Handoff queue',table(handoffs,[{label:'Case',key:'case_id'},{label:'Report',render:r=>esc(r.registry_report_id||'Not linked')},{label:'Status',render:r=>badge(r.status)},{label:'Created',render:r=>fmtDate(r.created_at)}]))+panel('Published reports',table(reports,[{label:'Case',key:'case_id'},{label:'Title',key:'title'},{label:'Published',render:r=>fmtDate(r.published_at)},{label:'State',render:r=>badge(r.revoked_at?'revoked':'published')}])));
  }
  if(view==='analytics'){
    const metrics=await Promise.all([count('intake_submissions'),count('case_memberships',x=>x.eq('active',true)),count('upload_records'),count('evidence_work_items',x=>x.in('status',['OPEN','IN_REVIEW'])),count('published_reports',x=>x.is('revoked_at',null)),count('invoices',x=>x.eq('status','PAID'))]);
    return workspaceLayout('admin','analytics','Analytics / KPIs','Operational counts only; not financial statements or audited metrics.',`<div class="grid-3">${[['Intakes',metrics[0]],['Active client-case memberships',metrics[1]],['Uploads received',metrics[2]],['Open evidence work items',metrics[3]],['Published reports',metrics[4]],['Paid invoices',metrics[5]]].map(([l,v])=>`<div class="card metric"><div class="metric-value">${v}</div><div class="metric-label">${esc(l)}</div></div>`).join('')}</div>`);
  }
  if(view==='billing'){
    const rows=await q('invoices','*',x=>x.order('created_at',{ascending:false}).limit(200));
    const total=rows.filter(r=>r.status==='PAID').reduce((a,r)=>a+Number(r.amount_cents||0),0);
    return workspaceLayout('admin','billing','Billing overview','Operational invoice ledger; not an accounting system of record.',`<div class="grid-3"><div class="card metric"><div class="metric-value">${fmtMoney(total)}</div><div class="metric-label">Recorded paid invoices</div></div><div class="card metric"><div class="metric-value">${rows.filter(r=>r.status==='OPEN').length}</div><div class="metric-label">Open</div></div><div class="card metric"><div class="metric-value">${rows.filter(r=>r.status==='PAST_DUE').length}</div><div class="metric-label">Past due</div></div></div>${panel('Invoices',table(rows,[{label:'Invoice',key:'invoice_number'},{label:'Case',key:'case_id'},{label:'Amount',render:r=>fmtMoney(r.amount_cents)},{label:'Status',render:r=>badge(r.status)},{label:'Due',render:r=>fmtDate(r.due_date)}]))}`);
  }
  if(view==='referrals'){
    const [partners,opps]=await Promise.all([q('referral_partners','*',x=>x.order('created_at',{ascending:false})),q('referral_opportunities','*',x=>x.order('created_at',{ascending:false}))]);
    const form=`<form id="referral-partner-form"><div class="form-grid"><div class="form-field"><label>Partner / firm name</label><input name="name" required /></div><div class="form-field"><label>Partner type</label><select name="partner_type"><option>Attorney</option><option>CPA / Accountant</option><option>Licensed Investigator</option><option>Business Consultant</option><option>Bookkeeper</option><option>Insurance Professional</option><option>Other Qualified Professional</option></select></div><div class="form-field"><label>Contact name</label><input name="contact_name" /></div><div class="form-field"><label>Contact email</label><input name="contact_email" type="email" /></div></div><div class="form-actions"><button class="btn btn-primary">Add partner</button></div></form>`;
    return workspaceLayout('admin','referrals','Referral pipeline','Professional relationships and prospective engagement flow.',panel('Add referral partner',form)+panel('Partners',table(partners,[{label:'Partner',key:'name'},{label:'Type',key:'partner_type'},{label:'Contact',render:r=>esc(r.contact_name||r.contact_email||'—')},{label:'Status',render:r=>badge(r.status)}]))+panel('Opportunities',table(opps,[{label:'Prospect',render:r=>esc(r.prospective_client_name||'Unidentified')},{label:'Status',render:r=>badge(r.status)},{label:'Next action',key:'next_action'},{label:'Date',render:r=>fmtDate(r.next_action_date)}])));
  }
  if(view==='capacity'){
    const rows=await q('case_assignments','*',x=>x.eq('active',true));
    const grouped=Object.values(rows.reduce((a,r)=>{a[r.staff_user_id]??={staff_user_id:r.staff_user_id,cases:new Set(),roles:new Set()};a[r.staff_user_id].cases.add(r.case_id);a[r.staff_user_id].roles.add(r.assignment_role);return a;},{})).map(x=>({staff_user_id:x.staff_user_id,cases:x.cases.size,roles:[...x.roles].join(', ')}));
    return workspaceLayout('admin','capacity','Capacity / workload','Assignment-based workload view; capacity targets remain configurable company policy.',panel('Active staff load',table(grouped,[{label:'Staff UUID',key:'staff_user_id'},{label:'Active cases',key:'cases'},{label:'Assignment roles',key:'roles'}])));
  }
  if(view==='health' || view==='security' || view==='backups'){
    const cfg=view==='health'?['system_health','System health','component','status','checked_at']:view==='security'?['security_alerts','Security alerts','title','status','detected_at']:['backup_status','Backup / recovery status','system','status','checked_at'];
    const rows=await q(cfg[0],'*',x=>x.order(cfg[4],{ascending:false}).limit(100));
    return workspaceLayout('admin',view,cfg[1],view==='health'?'Operational component observations; do not imply an uptime SLA.':view==='security'?'Security events requiring owner/admin visibility.':'Recorded backup observations; availability depends on the configured infrastructure.',panel(cfg[1],table(rows,[{label:view==='security'?'Alert':'System / component',key:cfg[2]},{label:'Status',render:r=>badge(r[cfg[3]])},{label:'Summary',render:r=>esc(r.summary||r.details||'—')},{label:'Checked / detected',render:r=>fmtDate(r[cfg[4]])}])));
  }
  if(view==='settings'){
    const rows=await q('app_settings','*',x=>x.order('key'));
    return workspaceLayout('admin','settings','Settings','Controlled operational configuration. Sensitive secrets do not belong in this table.',panel('Application settings',table(rows,[{label:'Key',key:'key'},{label:'Public read',render:r=>badge(r.public_read?'yes':'no')},{label:'Updated',render:r=>fmtDate(r.updated_at)},{label:'Value',render:r=>`<code class="micro">${esc(JSON.stringify(r.value).slice(0,240))}</code>`}]),'Google Calendar, Gmail, and Drive are recorded as planned integrations, not active claims.'));
  }
  return '';
}

async function sha256(file) {
  const buf=await file.arrayBuffer(); const hash=await crypto.subtle.digest('SHA-256',buf);
  return [...new Uint8Array(hash)].map(b=>b.toString(16).padStart(2,'0')).join('');
}
function cleanFilename(name){ return String(name).replace(/[^a-zA-Z0-9._-]+/g,'_').slice(-140); }
async function secureUpload(bucket,path,file){ const {error}=await supabase.storage.from(bucket).upload(path,file,{upsert:false,contentType:file.type||undefined});if(error)throw error; }

async function handleSubmit(e) {
  const f=e.target; if(!(f instanceof HTMLFormElement)) return; const id=f.id; if(!id) return;
  const known=['signin-form','contact-signin-form','profile-form','intake-form','engagement-form','upload-form','message-form','meeting-form','support-form','evidence-form','narrative-form','document-request-form','case-note-form','qa-form','handoff-form','assignment-form','service-form','template-form','publish-report-form','referral-partner-form'];
  if(!known.includes(id)) return; e.preventDefault(); const fd=new FormData(f); const button=f.querySelector('button[type="submit"],button:not([type])'); if(button)button.disabled=true;
  try {
    if(id==='signin-form'||id==='contact-signin-form'){
      const email=String(fd.get('email')).trim(); const {error}=await supabase.auth.signInWithOtp({email,options:{emailRedirectTo:`${location.origin}${location.pathname}#/portal/intake`}}); if(error)throw error; toast('Secure sign-in link sent. Check your email.','success');
    } else if(id==='profile-form'){
      const {error}=await supabase.from('profiles').update({display_name:fd.get('display_name'),phone:fd.get('phone')||null,organization_name:fd.get('organization_name')||null}).eq('id',state.user.id); if(error)throw error; await refreshAuth(); toast('Profile updated.','success');
    } else if(id==='intake-form'){
      const payload={user_id:state.user.id,status:'SUBMITTED',service_requested:fd.get('service_requested'),matter_summary:fd.get('matter_summary'),referral_source:fd.get('referral_source')||null,contact:{email:state.user.email,display_name:state.profile?.display_name,phone:state.profile?.phone},submitted_at:new Date().toISOString()}; const {error}=await supabase.from('intake_submissions').insert(payload); if(error)throw error; toast('Intake submitted for review.','success');
    } else if(id==='engagement-form'){
      const payload={user_id:state.user.id,intake_id:fd.get('intake_id')||null,case_id:state.activeCase||null,acknowledgement_type:'ENGAGEMENT_BOUNDARY_ACK',document_key:'standard_engagement_terms',document_version:'PLACEHOLDER-2026-09-DRAFT',signature_name:fd.get('signature_name'),accepted:true,accepted_at:new Date().toISOString(),metadata:{electronic_signature_placeholder:true}}; const {error}=await supabase.from('engagement_acceptances').insert(payload); if(error)throw error; toast('Acknowledgment recorded.','success');
    } else if(id==='upload-form'){
      const file=fd.get('file'); if(!(file instanceof File)||!file.size)throw new Error('Choose a file.'); const destination=fd.get('destination'); let case_id=null,intake_id=null,path; const stamp=Date.now(); const name=cleanFilename(file.name); if(destination==='case'){case_id=state.activeCase;if(!case_id)throw new Error('No authorized case selected.');path=`case/${case_id}/${state.user.id}/${stamp}-${name}`;}else{const latest=(await q('intake_submissions','id',x=>x.eq('user_id',state.user.id).order('created_at',{ascending:false}).limit(1)))[0];if(!latest)throw new Error('Submit intake before uploading to intake.');intake_id=latest.id;path=`intake/${state.user.id}/${intake_id}/${stamp}-${name}`;} const hash=await sha256(file); await secureUpload('client-documents',path,file); const {error}=await supabase.from('upload_records').insert({case_id,intake_id,uploaded_by:state.user.id,storage_bucket:'client-documents',storage_path:path,original_filename:file.name,mime_type:file.type||null,size_bytes:file.size,sha256:hash,status:'RECEIVED'}); if(error)throw error; toast('File uploaded to private storage.','success');
    } else if(id==='message-form'){
      const {error}=await supabase.from('portal_messages').insert({case_id:state.activeCase,sender_id:state.user.id,body:fd.get('body'),thread_type:'CLIENT'}); if(error)throw error; toast('Message sent.','success');
    } else if(id==='meeting-form'){
      const {error}=await supabase.from('meeting_requests').insert({case_id:state.activeCase,user_id:state.user.id,topic:fd.get('topic'),preferred_slots:[fd.get('slot')],notes:fd.get('notes')||null}); if(error)throw error; toast('Meeting request submitted.','success');
    } else if(id==='support-form'){
      const {error}=await supabase.from('support_tickets').insert({user_id:state.user.id,case_id:state.activeCase||null,category:fd.get('category'),subject:fd.get('subject'),body:fd.get('body')}); if(error)throw error; toast('Support request opened.','success');
    } else if(id==='evidence-form'){
      const payload={case_id:state.activeCase,queue_type:fd.get('queue_type'),evidence_state:fd.get('evidence_state')||null,source_id:fd.get('source_id')||null,proposition_id:fd.get('proposition_id')||null,summary:fd.get('summary'),internal_notes:fd.get('internal_notes')||null,assignee_id:state.user.id}; const {error}=await supabase.from('evidence_work_items').insert(payload); if(error)throw error; toast('Evidence work item added.','success');
    } else if(id==='narrative-form'){
      const {error}=await supabase.from('review_narratives').insert({case_id:state.activeCase,author_id:state.user.id,narrative:fd.get('narrative'),status:fd.get('status')}); if(error)throw error; toast('Review narrative saved.','success');
    } else if(id==='document-request-form'){
      const {error}=await supabase.from('document_requests').insert({case_id:state.activeCase,title:fd.get('title'),description:fd.get('description')||null,requested_by:state.user.id,due_date:fd.get('due_date')||null,client_visible:fd.get('client_visible')==='on'}); if(error)throw error; toast('Document request created.','success');
    } else if(id==='case-note-form'){
      const {error}=await supabase.from('case_notes').insert({case_id:state.activeCase,author_id:state.user.id,note_type:fd.get('note_type'),body:fd.get('body')}); if(error)throw error; toast('Private case note saved.','success');
    } else if(id==='qa-form'){
      const status=fd.get('status'); const payload={case_id:state.activeCase,item_key:fd.get('item_key'),label:fd.get('label'),status,notes:fd.get('notes')||null,completed_by:status==='PENDING'?null:state.user.id,completed_at:status==='PENDING'?null:new Date().toISOString()}; const {error}=await supabase.from('qa_checklists').upsert(payload,{onConflict:'case_id,item_key'}); if(error)throw error; toast('QA item saved.','success');
    } else if(id==='handoff-form'){
      const {error}=await supabase.from('publication_handoffs').insert({case_id:state.activeCase,registry_report_id:fd.get('registry_report_id')||null,status:fd.get('status'),prepared_by:state.user.id,internal_notes:fd.get('internal_notes')||null}); if(error)throw error; toast('Publication handoff created.','success');
    } else if(id==='assignment-form'){
      const {error}=await supabase.from('case_assignments').insert({case_id:fd.get('case_id'),staff_user_id:fd.get('staff_user_id'),assignment_role:fd.get('assignment_role'),assigned_by:state.user.id}); if(error)throw error; await refreshCases(); toast('Case assignment created.','success');
    } else if(id==='service-form'){
      const {error}=await supabase.from('service_definitions').insert({service_key:fd.get('service_key'),name:fd.get('name'),summary:fd.get('summary'),scope_text:fd.get('scope_text')||null,delivery_text:fd.get('delivery_text')||null,public_visible:true,active:true}); if(error)throw error; await loadPublicData(); toast('Service definition added.','success');
    } else if(id==='template-form'){
      const {error}=await supabase.from('template_catalog').insert({template_key:fd.get('template_key'),name:fd.get('name'),template_type:fd.get('template_type'),version:fd.get('version'),description:fd.get('description')||null}); if(error)throw error; toast('Template record added.','success');
    } else if(id==='publish-report-form'){
      const file=fd.get('file'); const caseId=String(fd.get('case_id')).trim(); if(!(file instanceof File)||!file.size)throw new Error('Choose the approved PDF.'); const version=Number(fd.get('version')); const path=`case/${caseId}/${Date.now()}-${cleanFilename(file.name)}`; const hash=await sha256(file); await secureUpload('published-reports',path,file); const {error}=await supabase.from('published_reports').insert({case_id:caseId,title:fd.get('title'),report_type:fd.get('report_type'),version,storage_path:path,sha256:hash,published_by:state.user.id,published_at:new Date().toISOString(),client_visible:true}); if(error)throw error; toast('Approved report published to the client delivery store.','success');
    } else if(id==='referral-partner-form'){
      const {error}=await supabase.from('referral_partners').insert({name:fd.get('name'),partner_type:fd.get('partner_type'),contact_name:fd.get('contact_name')||null,contact_email:fd.get('contact_email')||null}); if(error)throw error; toast('Referral partner added.','success');
    }
    f.reset(); await render();
  } catch(err) { console.error(err); toast(err.message || 'The operation could not be completed.','error'); }
  finally { if(button)button.disabled=false; }
}

async function handleClick(e) {
  const btn=e.target.closest('[data-action]'); if(!btn)return; const action=btn.dataset.action;
  try {
    if(action==='signout'){ await supabase.auth.signOut(); await refreshAuth(); go('/home'); }
    if(action==='download-report'){ const {data,error}=await supabase.storage.from('published-reports').createSignedUrl(btn.dataset.path,60); if(error)throw error; window.open(data.signedUrl,'_blank','noopener'); }
    if(action==='save-role'){ const user=btn.dataset.user; const role=document.querySelector(`[data-role-user="${CSS.escape(user)}"]`)?.value; const {error}=await supabase.rpc('admin_set_user_role',{target_user_id:user,target_role:role}); if(error)throw error; toast('Role updated.','success'); await render(); }
  } catch(err){console.error(err);toast(err.message||'Action failed.','error');}
}
async function handleChange(e) {
  if(e.target.id==='case-selector'){ state.activeCase=e.target.value; localStorage.setItem('coletti.activeCase',state.activeCase); await render(); }
  if(e.target.dataset.action==='intake-status'){ const {error}=await supabase.from('intake_submissions').update({status:e.target.value}).eq('id',e.target.dataset.id); if(error)toast(error.message,'error'); else {toast('Intake status updated.','success');await render();} }
}

async function render() {
  renderHeader(); renderFooter(); $('#app-banner').innerHTML='';
  const p=route(); let html='';
  try {
    if(p==='/home')html=homePage();
    else if(p==='/services')html=servicesPage();
    else if(p==='/how-it-works')html=howPage();
    else if(p==='/about')html=aboutPage();
    else if(p==='/referral-partners')html=referralsPage();
    else if(p==='/pricing')html=pricingPage();
    else if(p==='/security')html=securityPage();
    else if(p==='/faq')html=faqPage();
    else if(p==='/contact')html=contactPage();
    else if(p==='/disclaimer')html=legalPage('disclaimer');
    else if(p==='/privacy')html=legalPage('privacy');
    else if(p==='/terms')html=legalPage('terms');
    else if(p==='/sign-in')html=signInPage();
    else if(p.startsWith('/portal/'))html=await portalPage(p.split('/')[2]||'home');
    else if(p.startsWith('/workspace/'))html=await staffPage(p.split('/')[2]||'home');
    else if(p.startsWith('/admin/'))html=await adminPage(p.split('/')[2]||'home');
    else html=`${publicHero('Page not found.','The requested page is not available.','404')}<section class="section"><div class="container"><a class="btn btn-primary" href="#/home">Return home</a></div></section>`;
  } catch(err) { console.error(err); html=`<section class="section"><div class="container"><div class="notice notice-danger"><strong>Workspace error</strong><br/>${esc(err.message||'The requested data could not be loaded.')}</div></div></section>`; }
  $('#main').innerHTML=html; window.scrollTo(0,0);
}

window.addEventListener('hashchange',render);
document.addEventListener('submit',handleSubmit);
document.addEventListener('click',handleClick);
document.addEventListener('change',handleChange);
supabase.auth.onAuthStateChange(async()=>{await refreshAuth();await render();});

await loadPublicData();
await refreshAuth();
await render();
