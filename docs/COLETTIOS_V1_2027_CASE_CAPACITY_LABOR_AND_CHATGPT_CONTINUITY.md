# ColettiOS V1 Unified Release 2027 — Solo Capacity, Human Labor & Subscription Continuity

**October 12, 2026 | Planning model, NOT measured production capacity or financial advice.** The current project contains no completed, authorized external-client case or accepted real production hour ledger. No changes to live rates, client promises, release permissions, API billing, credentials, or deployment.

## A. Founder operating assumptions

Founder availability planning scenarios: **22 hours/week** (previous operating target) and **40 hours/week** (full-time hypothetical). Reserve **40%** of founder hours for client development/sales, consultations, business administration, finance, customer support, maintenance, and exceptions. Thus monthly production capacity at 4.33 weeks/month:

- 22 h/week * 4.33 * 60% = **57.2 founder case-production hours/month**.
- 40 h/week * 4.33 * 60% = **103.9 founder case-production hours/month**.

A standard fully governed V1 matter including independent human QA is assumed at **28–50 total human hours**, with a central calibration **26 founder hours + 5 external reviewer hours = 31 total**. The exact case split must be tracked. A separate qualified human is required wherever independent Fresh Eyes/QA must not be self-certified; a sole founder can operate without a full-time employee, but not claim independent QA solely by AI or self-review.

- 22-hour-week scenario: 57/26 = 2.20 standard-equivalent cases/month theoretical. **Contract no more than 1–2 full-standard completions/month initially** while pilot data is unknown; add a small diagnostic only with slack. Two production-intensive standard cases simultaneously max starting posture.
- 40-hour-week scenario: 104/26 = 4.0 standard equivalents/month theoretical; **3–4/month** only after measured performance, protected QA capacity and established communications/delivery reliability.
- Never promise these throughput figures before the 5-case paid pilot and accepted normal-path experience. Case concurrency is not identical to throughput: waiting-on-client cases may be open but not consuming equivalent production hours.

## B. Case scope, labor and published turnaround assumptions

| Class | Indicative human hours INCLUDING QA | Time from usable intake to authorized report, business days | Illustrative substantive volume; not an unconditional hard cap |
| --- | --- | --- | --- |
| Diagnostic | 6–12 | 3–7 | 10–30 relevant source items, ~50–200 pages |
| Focused reconstruction | 14–25 | 7–15 | 30–100 items, ~150–600 pages, 1–3 systems |
| Standard full | 28–50 | 15–25 | 80–250 items, ~500–1,500 pages, 2–5 systems |
| Complex | 60–120 | 30–50 (6–10 weeks) | 250–700+ items, ~1,500–5,000 pages, several entities and disputed issues |
| Exceptional large | 120–250+ | 50–80+ (10–16+ weeks) | Multi-year / cross-organization / high-dispute; phased pricing/milestones |

**Source-items are distinct relevant artifacts, not merely file count.** A 5,000-page monotonous statement export may be easier than 100 contradictory emails across 3 people. Clock starts only when agreed minimum usable source intake and authorization are satisfied; client wait, scope changes and reviewer rework separately tracked. Source parsing quality is a major labor driver. All quoted client deadlines must reserve human QA/publication and corrections.

Standard-case estimated allocation: Qualification/scope 2–4h; source intake/verification 4–8h; reconstruction 8–14h; adversarial-pair investigation 2–4h; report/citation corrections 4–8h; independent human QA 4–8h; client communication/approved handoff 3–5h. Ranges overlap; central example is 26 founder + 5 reviewer = 31 hours. Extra professional handoff only if actually authorized/contracted, with change-order mechanism for scope excess.

### Weighted demand units

Define **1 standard-equivalent unit (SEU) = 26 founder production hours**, initially.
- Diagnostic: 0.25–0.45 SEU;
- Focused: 0.5–0.85 SEU;
- Standard: 1.0 SEU;
- Complex: 2.3–4.0 SEU;
- Exceptional: 4.5–9+ SEU.

One 75-founder-hour complex case can consume approximately 3 standard equivalents. Maximum active case count should also require hard limits for deadline collisions, source backlog, human-review availability, staff capacity and exceptions.

## C. Price-versus-cost (illustrative standard case)

The following are **internal burden/opportunity costs and hypothetical contractor rates**, not supplier invoices or BLS consulting fees. BLS May 2025 median pay as benchmark: management analyst $101,860/year; accountant/auditor $83,680/year; paralegal $62,890/year. Current wage and actual specialist contractor quotes vary.

- Founder 26h × $60 imputed economic cost = $1,560.
- Independent reviewer 5h × $95 actual illustrative paid labor = $475.
- Allocated AI/document/tool cost = $90.
- Allocated admin/overhead = $250.
- Illustrative payment processing = $150.
- **Total modeled economic cost $2,525**. $5,000 case price less cost = **$2,475 / 49.5% modeled contribution** before unallocated expenses, taxes, CAC spikes, significant rework and underwriting risk.

Suggested costing allowance (not fee quotes): founder $50–75 productive hour; record analyst contractor $45–80; independent professional-quality reviewer $75–125; admin support $25–40. Separate economic value of founder time from **cash actually leaving the account**: in this example the founder's $1,560 is imputed, not an invoice. Measure realized case economics before hiring based on paper profit.

## D. Human staffing thresholds

- **From the first full case:** secure a suitable independent human QA/Fresh Eyes contract/reviewer under NDA and case confidentiality/qualification requirements wherever policy requires genuine reviewer independence. AI pairing is not a substitute.
- **Founder 22h/week posture:** booking three standard equivalents in one month at 26 founder hours each requires ~78 founder production hours—greater than ~57 available. Stagger work or engage an analyst before committing.
- **Analyst contractor/hire trigger:** >60–80 hours/month of genuinely delegable, funded reconstruction work across consecutive months; backlog over 3–4 weeks; deadline risk; repeatable evidence QA issues; or demand of >2 standard-equivalent matters/month with founder on 22-hour schedule. Begin part-time and prove quality rather than hiring full-time based on a single high-revenue month.
- **Capacity preservation:** stop new commitments or use qualified scoped subcontractors when forecast utilization exceeds 80% of founder case-production capacity for the next 30 days, independently of nominal open-case count; leave 20% capacity for client late files, correction, redaction and system incidents.
- **True hiring ROI:** margin on incremental cases must exceed contractor wages, management/training, insurance/security, QA/rework and integration effort. New case workers require real Supabase Auth/RBAC acceptance and supervised assigned-case access.

## E. Subscription-independent DARI operational continuity

The ChatGPT app/ChatGPT subscription is **not** the production runtime or long-term authoritative storage. ChatGPT subscription billing and OpenAI API billing are separate. A downgrade from Plus may reduce app limits/plugin availability but must not disable deployed business operations.

Design requirements:
1. Native authenticated DARI UI works on canonical /workspace/ using a separately authorized, separately billed OpenAI API project/service, with budget thresholds, hard-stop limits and live usage tracing.
2. Server-side credentials, model provider-neutral routing and cached validated deterministic Core rules; prefer NO_AI for stable lookups and scoped small models for extraction; escalate to stronger models when needed. Avoid reprocessing unchanged source snapshots; do not claim deterministic mode can perform adversarial AI analysis.
3. Supabase institutional and private approved DOMUS preference stores own durable context. DARI's skill/specifications/code/runbooks remain in GitHub; **never store sensitive personal memory/plain source records in a public repository**. Selected ChatGPT history transfer requires explicit authorization/ingest.
4. Clear degraded states: CHATGPT_UI_UNAVAILABLE, PLUGIN_UNAVAILABLE, MODEL_PROVIDER_UNAVAILABLE, API_CREDITS_EXHAUSTED and SYSTEM_RECORDS_AVAILABLE; queue AI-required work as HOLD, preserve data, communicate truthful delays and require human sign-off.
5. Test authenticated business continuity with no ChatGPT Plus access and separately test zero API credits, revoked OAuth, expired plugin permissions, provider timeouts and fallback/restore. No plan workaround that circumvents subscription limits.
6. Codex/ChatGPT development allowance is not production API availability; GitHub CI and pinned source retain reproducible build evidence, but autonomous software changes still need authorized deployment and testing.
7. API rate/budget and provider-specific privacy/retention controls must be assessed; model and pricing changes require tested adapter upgrades, not emergency architecture rewrites.

Official docs: https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform ; https://developers.openai.com/api/docs/pricing ; https://help.openai.com/en/articles/6614457-troubleshooting-api-usage-and-spend-limits ; https://help.openai.com/en/articles/20001256-plugins-in-chatgpt .

## F. Pilot measurement / 90-day stability metrics

**Every paid case**: intake acceptance time, client wait time, unique source items, pages, number of independent systems, date range, entities, contradictions, disputed claims, deficient sources, AI model/token/tool usage, founder production hours (by workflow phase), contractor QA hours and expenses, number of rework loops, release elapsed business days, delivery/access results, fees/refunds and all actual/direct plus allocated economic cost.

**After first five authorized completed engagements**: calculate median, 75th and 90th percentile founder and review time, margin and turnaround by complexity. Use measured distributions, not marketing promises. Recalibrate standard-equivalent weights and limits. One heavily abnormal case should trigger category redesign/change order, not silently rewrite the baseline.

**Do not represent the ranges as production capabilities** while the end-to-end actual client publication case and independent QA acceptance remain unproved. Freeze term begins only after verified external-client activation and acceptance.
