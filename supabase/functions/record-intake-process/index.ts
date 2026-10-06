import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.115.0";
import { extractText, getDocumentProxy } from "npm:unpdf@1.8.1";

type Upload = {
  id: string; case_id: string | null; intake_id: string | null; uploaded_by: string;
  storage_bucket: string; storage_path: string; original_filename: string;
  mime_type: string | null; size_bytes: number | null; source_id: string | null;
};
type Job = {
  id: string; upload_id: string; case_id: string | null; status: string; route: string;
  suggested_taxonomy_key: string | null; suggested_source_type: string | null;
  suggested_source_role: string | null; suggested_client_label: string | null;
  classification_confidence: number | null; bundle_state: string | null; extracted_metadata: Record<string, unknown> | null;
};

const MAX_FILE_BYTES = 40 * 1024 * 1024;
const MAX_PDF_PAGES = 250;
const MAX_ANALYSIS_CHARS = 1_200_000;
const PROCESSOR_VERSION = "record_content_processor_v1.0.1";
const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "authorization, x-client-info, apikey, content-type",
  "access-control-allow-methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS, "content-type": "application/json; charset=utf-8" },
  });
}
function parseNamedKey(envName: string, fallbackName: string): string {
  const raw = Deno.env.get(envName);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (typeof parsed?.default === "string" && parsed.default) return parsed.default;
    } catch {}
  }
  return Deno.env.get(fallbackName) ?? "";
}
function publishableKey() { return parseNamedKey("SUPABASE_PUBLISHABLE_KEYS", "SUPABASE_ANON_KEY"); }
function secretKey() { return parseNamedKey("SUPABASE_SECRET_KEYS", "SUPABASE_SERVICE_ROLE_KEY"); }
function cleanName(name: string) {
  return name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
}
function normalizeText(input: string) {
  return input.toLowerCase().normalize("NFKC").replace(/[^a-z0-9$%./:@ -]+/g, " ")
    .replace(/\s+/g, " ").trim().slice(0, MAX_ANALYSIS_CHARS);
}
async function sha256Hex(input: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function fnv1a64(input: string) {
  let h = 0xcbf29ce484222325n;
  const prime = 0x100000001b3n;
  const mask = 0xffffffffffffffffn;
  for (const b of new TextEncoder().encode(input)) {
    h ^= BigInt(b);
    h = (h * prime) & mask;
  }
  return h;
}
function simhash64(text: string) {
  const tokens = text.split(/\s+/).filter((x) => x.length > 2).slice(0, 12000);
  if (!tokens.length) return null;
  const weights = new Int32Array(64);
  for (let i = 0; i < tokens.length; i++) {
    const shingle = [tokens[i], tokens[i + 1] ?? "", tokens[i + 2] ?? ""].join(" ");
    const h = fnv1a64(shingle);
    for (let bit = 0; bit < 64; bit++) weights[bit] += ((h >> BigInt(bit)) & 1n) ? 1 : -1;
  }
  let out = 0n;
  for (let bit = 0; bit < 64; bit++) if (weights[bit] >= 0) out |= 1n << BigInt(bit);
  return out.toString(16).padStart(16, "0");
}
function hammingHex(a: string, b: string) {
  let x = BigInt("0x" + a) ^ BigInt("0x" + b), n = 0;
  while (x) { n += Number(x & 1n); x >>= 1n; }
  return n;
}

const TYPE_MAP: Record<string, { sourceType: string; role: string }> = {
  financial_bank_statement: { sourceType: "Financial Record", role: "NATIVE_SOURCE" },
  financial_credit_card_statement: { sourceType: "Financial Record", role: "NATIVE_SOURCE" },
  financial_tax_record: { sourceType: "Financial Record", role: "NATIVE_SOURCE" },
  business_invoice: { sourceType: "Business Record", role: "NATIVE_SOURCE" },
  business_receipt: { sourceType: "Business Record", role: "NATIVE_SOURCE" },
  correspondence_email: { sourceType: "Correspondence", role: "NATIVE_SOURCE" },
  correspondence_letter: { sourceType: "Correspondence", role: "NATIVE_SOURCE" },
  agreement_contract: { sourceType: "Agreement", role: "NATIVE_SOURCE" },
  court_filing: { sourceType: "Court Filing", role: "NATIVE_SOURCE" },
  government_record: { sourceType: "Government Record", role: "NATIVE_SOURCE" },
  spreadsheet_data_export: { sourceType: "Data Export", role: "NATIVE_SOURCE" },
  photograph_image: { sourceType: "Image", role: "NATIVE_SOURCE" },
  audio_video: { sourceType: "Media", role: "NATIVE_SOURCE" },
  identity_organizational: { sourceType: "Identity / Organizational Record", role: "NATIVE_SOURCE" },
  other_unclassified: { sourceType: "Other", role: "OTHER" },
};

type Rule = { key: string; patterns: Array<[RegExp, number]> };
const RULES: Rule[] = [
  { key: "financial_bank_statement", patterns: [
    [/\baccount summary\b/i, 2], [/\bbeginning balance\b/i, 2], [/\bending balance\b/i, 2],
    [/\bstatement (period|date)\b/i, 2], [/\bdeposits?\b/i, 0.6], [/\bwithdrawals?\b/i, 0.6],
  ]},
  { key: "financial_credit_card_statement", patterns: [
    [/\bcredit card\b/i, 2], [/\bminimum payment due\b/i, 2], [/\bcredit limit\b/i, 2],
    [/\bpayment due date\b/i, 1.5], [/\bnew balance\b/i, 1],
  ]},
  { key: "financial_tax_record", patterns: [
    [/\bform\s+(1040|w-?2|1099[-a-z0-9]*)\b/i, 3], [/internal revenue service/i, 2],
    [/\btax year\b/i, 1.5],
  ]},
  { key: "business_invoice", patterns: [
    [/\binvoice\b/i, 3], [/\bamount due\b/i, 2], [/\bbill to\b/i, 1.5], [/\binvoice\s*#?\s*[:\w-]+/i, 1],
  ]},
  { key: "business_receipt", patterns: [
    [/\breceipt\b/i, 3], [/\bsubtotal\b/i, 1.2], [/\btotal\b/i, 0.8], [/\bthank you for your purchase\b/i, 1],
  ]},
  { key: "correspondence_email", patterns: [
    [/^from:\s*.+/mi, 2], [/^to:\s*.+/mi, 1.5], [/^subject:\s*.+/mi, 2], [/^(sent|date):\s*.+/mi, 1],
  ]},
  { key: "correspondence_letter", patterns: [
    [/\bdear\s+[a-z]/i, 1.5], [/\bsincerely\b/i, 1], [/\bre:\s*.+/i, 1.2], [/\bto whom it may concern\b/i, 2],
  ]},
  { key: "agreement_contract", patterns: [
    [/\b(this\s+)?agreement\b/i, 2], [/\bparties\b/i, 1], [/\bterms and conditions\b/i, 1.5],
    [/\bsignature\b/i, 1], [/\bexecuted\b/i, 0.8],
  ]},
  { key: "court_filing", patterns: [
    [/\bin the .{0,80} court\b/i, 3], [/\bcase\s*(no\.?|number)\b/i, 2],
    [/\b(petitioner|plaintiff)\b/i, 1], [/\b(respondent|defendant)\b/i, 1],
    [/\b(order|motion|petition|complaint|decree)\b/i, 1],
  ]},
  { key: "government_record", patterns: [
    [/\b(united states|state of|department of|office of)\b/i, 1.2],
    [/\b(agency|government|social security administration|department of revenue)\b/i, 1.8],
  ]},
  { key: "identity_organizational", patterns: [
    [/\b(driver'?s license|passport)\b/i, 3], [/\barticles of (organization|incorporation)\b/i, 3],
    [/\bcertificate of (formation|incorporation)\b/i, 3],
  ]},
];

function classify(text: string, filename: string, existingKey?: string | null, existingConfidence?: number | null) {
  const sample = text.slice(0, 250000);
  let best = { key: existingKey || "other_unclassified", score: 0, confidence: Number(existingConfidence || 0.4) };
  for (const rule of RULES) {
    let score = 0;
    for (const [rx, weight] of rule.patterns) if (rx.test(sample)) score += weight;
    if (rule.key === existingKey) score += 0.75;
    const confidence = Math.min(0.995, 0.48 + score * 0.09);
    if (score > best.score || (score === best.score && confidence > best.confidence)) best = { key: rule.key, score, confidence };
  }
  const lower = filename.toLowerCase();
  if (/\.(csv|xlsx?|ods)$/i.test(lower)) return { key: "spreadsheet_data_export", confidence: 0.995 };
  if (/\.(png|jpe?g|webp|heic|tiff?)$/i.test(lower)) return { key: "photograph_image", confidence: 0.995 };
  if (/\.(mp3|wav|m4a|mp4|mov|avi|mkv)$/i.test(lower)) return { key: "audio_video", confidence: 0.995 };
  return { key: best.key, confidence: Math.max(best.confidence, existingKey === best.key ? Number(existingConfidence || 0) : 0) };
}

function looksLikeDocumentStart(text: string) {
  const head = text.slice(0, 1400);
  return /\bpage\s+1\s+(of|\/)\s*\d+/i.test(head)
    || /^\s*(invoice|statement|agreement|contract|receipt)\b/im.test(head)
    || /^\s*from:\s*.+\n\s*(to|sent|date|subject):/im.test(head)
    || /\bin the .{0,80} court\b/i.test(head)
    || /^\s*(dear\s+|to whom it may concern)/im.test(head);
}
function proposeSegments(pages: string[], filename: string) {
  if (pages.length <= 1) return [];
  const starts = [0];
  let previous = classify(pages[0].slice(0, 6000), filename);
  for (let i = 1; i < pages.length; i++) {
    const current = classify(pages[i].slice(0, 6000), filename);
    const strong = looksLikeDocumentStart(pages[i]);
    const categoryShift = current.key !== previous.key && current.confidence >= 0.78;
    if (strong && (categoryShift || /\bpage\s+1\s+(of|\/)\s*\d+/i.test(pages[i].slice(0, 1200)))) starts.push(i);
    previous = current;
  }
  if (starts.length <= 1) return [];
  const segments = [];
  for (let i = 0; i < starts.length; i++) {
    const start = starts[i];
    const end = (starts[i + 1] ?? pages.length) - 1;
    const c = classify(pages.slice(start, Math.min(end + 1, start + 3)).join("\n").slice(0, 30000), filename);
    const mapped = TYPE_MAP[c.key] ?? TYPE_MAP.other_unclassified;
    segments.push({
      segment_index: i + 1, page_start: start + 1, page_end: end + 1,
      taxonomy_key: c.key, source_type: mapped.sourceType, source_role: mapped.role,
      client_label: `${cleanName(filename)} — pages ${start + 1}-${end + 1}`,
      confidence: Number(c.confidence.toFixed(3)),
      metadata: { proposed_by: PROCESSOR_VERSION, boundary_basis: "content_start_heuristic" },
    });
  }
  return segments;
}

const STOP = new Set(["the","and","for","that","this","with","from","your","you","are","was","were","have","has","not","into","our","their","its","of","to","in","on","at","a","an","or","by","as","is","be"]);
function termSet(text: string) {
  return new Set(normalizeText(text).split(/\s+/).filter((t) => t.length >= 4 && !STOP.has(t)).slice(0, 15000));
}
function requestMatches(requests: any[], text: string) {
  if (!text || text.length < 100) return [];
  const doc = termSet(text);
  const out: any[] = [];
  for (const r of requests) {
    const terms = [...termSet(`${r.title ?? ""} ${r.description ?? ""}`)];
    if (!terms.length) continue;
    const hits = terms.filter((t) => doc.has(t));
    const score = hits.length / terms.length;
    if (hits.length >= 2 && score >= 0.30) out.push({
      request_id: r.id,
      confidence: Math.min(0.95, Number((0.55 + score * 0.4).toFixed(3))),
      reason: `Content overlap: ${hits.slice(0, 8).join(", ")}`,
      metadata: { proposed_by: PROCESSOR_VERSION, terms_matched: hits.length, terms_considered: terms.length },
    });
  }
  return out.sort((a, b) => b.confidence - a.confidence).slice(0, 5);
}

async function processUpload(admin: any, upload: Upload, job: Job) {
  try {
    const exceptions: string[] = [];
    let pageCount: number | null = null;
    let pages: string[] = [];
    let text = "";
    let extraction = "METADATA_ONLY";

    if ((upload.size_bytes ?? 0) > MAX_FILE_BYTES) {
      exceptions.push("FILE_TOO_LARGE_FOR_CONTENT_PROCESSOR");
    } else if ((upload.mime_type || "").toLowerCase() === "application/pdf" || /\.pdf$/i.test(upload.original_filename)) {
      const { data: blob, error: dlError } = await admin.storage.from(upload.storage_bucket).download(upload.storage_path);
      if (dlError || !blob) throw dlError || new Error("storage_download_failed");
      const bytes = new Uint8Array(await blob.arrayBuffer());
      const pdf = await getDocumentProxy(bytes, { maxImageSize: 16_777_216 });
      pageCount = pdf.numPages;
      if (pageCount > MAX_PDF_PAGES) {
        exceptions.push("PDF_PAGE_LIMIT_EXCEEDED");
      } else {
        const extracted: any = await Promise.race([
          extractText(pdf, { mergePages: false }),
          new Promise((_, reject) => setTimeout(() => reject(new Error("pdf_text_extraction_timeout")), 45000)),
        ]);
        pages = Array.isArray(extracted.text) ? extracted.text.map((x: unknown) => String(x ?? "")) : [String(extracted.text ?? "")];
        text = pages.join("\n").slice(0, MAX_ANALYSIS_CHARS);
        extraction = "PDF_TEXT";
        const average = pages.length ? text.length / pages.length : 0;
        if (text.trim().length < 120 || average < 60) exceptions.push("TEXT_EXTRACTION_SPARSE_OR_SCAN");
      }
    } else if ((upload.mime_type || "").startsWith("text/") || /\.(txt|csv|eml)$/i.test(upload.original_filename)) {
      const { data: blob, error: dlError } = await admin.storage.from(upload.storage_bucket).download(upload.storage_path);
      if (dlError || !blob) throw dlError || new Error("storage_download_failed");
      text = (await blob.text()).slice(0, MAX_ANALYSIS_CHARS);
      pages = [text]; pageCount = 1; extraction = "TEXT";
    }

    const c = classify(text, upload.original_filename, job.suggested_taxonomy_key, job.classification_confidence);
    const normalized = normalizeText(text);
    const normalizedHash = normalized ? await sha256Hex(normalized) : null;
    const simhash = normalized ? simhash64(normalized) : null;
    const segments = pageCount && pages.length ? proposeSegments(pages, upload.original_filename) : [];

    let versionFamily: string | null = null;
    let versionCandidateJobId: string | null = null;
    if (upload.case_id && simhash && normalizedHash) {
      const { data: candidates } = await admin.from("record_intake_jobs")
        .select("id,upload_id,suggested_taxonomy_key,probable_version_family_key,extracted_metadata")
        .eq("case_id", upload.case_id).neq("upload_id", upload.id).limit(250);
      let closest: any = null, closestDistance = 65;
      for (const candidate of candidates ?? []) {
        const other = candidate?.extracted_metadata?.simhash64;
        const otherHash = candidate?.extracted_metadata?.normalized_text_sha256;
        if (!other || !otherHash || otherHash === normalizedHash) continue;
        if (candidate.suggested_taxonomy_key && candidate.suggested_taxonomy_key !== c.key) continue;
        try {
          const distance = hammingHex(simhash, String(other));
          if (distance < closestDistance) { closestDistance = distance; closest = candidate; }
        } catch {}
      }
      if (closest && closestDistance <= 8) {
        versionCandidateJobId = String(closest.id);
        versionFamily = closest.probable_version_family_key || `VF-${String(closest.id).replace(/-/g, "").slice(0, 16)}`;
      }
    }

    let matches: any[] = [];
    if (upload.case_id && text.length >= 100) {
      const { data: requests } = await admin.from("document_requests")
        .select("id,title,description,status").eq("case_id", upload.case_id)
        .in("status", ["OPEN","UPLOADED","UNDER_REVIEW"]);
      matches = requestMatches(requests ?? [], text);
    }

    const bundleState = segments.length > 1
      ? "PROBABLE_BUNDLE"
      : (job.bundle_state === "PROBABLE_BUNDLE" ? "PROBABLE_BUNDLE" : "SINGLE");

    const metadata = {
      processor_version: PROCESSOR_VERSION,
      extraction,
      text_character_count: text.length,
      normalized_text_sha256: normalizedHash,
      simhash64: simhash,
      content_analyzed_at: new Date().toISOString(),
      raw_text_persisted: false,
      classification_basis: text.length ? "content_plus_metadata" : "metadata_only",
      segment_proposal_only: true,
      request_match_proposal_only: true,
      probable_version_job_id: versionCandidateJobId,
    };

    const { error: rpcError } = await admin.rpc("apply_record_intake_analysis_v1", {
      p_upload_id: upload.id,
      p_taxonomy_key: c.key,
      p_confidence: Number(c.confidence.toFixed(3)),
      p_client_label: job.suggested_client_label || cleanName(upload.original_filename),
      p_page_count: pageCount,
      p_bundle_state: bundleState,
      p_segments: segments,
      p_metadata: metadata,
      p_version_family_key: versionFamily,
      p_exception_codes: exceptions,
      p_request_matches: matches,
    });
    if (rpcError) throw rpcError;
  } catch (error) {
    console.error("record-intake-process failed", upload.id, error);
    const current = Array.isArray((job as any)?.exception_codes) ? (job as any).exception_codes : [];
    await admin.from("record_intake_jobs").update({
      status: "FAILED", route: "RED",
      exception_codes: [...new Set([...current, "CONTENT_PROCESSOR_FAILED"])],
      failure_reason: String((error as any)?.message ?? error).slice(0, 500),
      processor_version: PROCESSOR_VERSION, updated_at: new Date().toISOString(),
    }).eq("upload_id", upload.id);
  }
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405);

  const url = Deno.env.get("SUPABASE_URL") ?? "";
  const pub = publishableKey(), secret = secretKey();
  if (!url || !pub || !secret) return json({ error: "supabase_not_configured" }, 503);

  const authHeader = req.headers.get("authorization") ?? "";
  if (!authHeader.startsWith("Bearer ")) return json({ error: "authentication_required" }, 401);

  const userClient = createClient(url, pub, { global: { headers: { Authorization: authHeader } } });
  const { data: authData, error: authError } = await userClient.auth.getUser();
  if (authError || !authData.user) return json({ error: "invalid_session" }, 401);

  let body: any;
  try { body = await req.json(); } catch { return json({ error: "invalid_json" }, 400); }
  const uploadId = String(body?.upload_id ?? "").trim();
  if (!/^[0-9a-f-]{36}$/i.test(uploadId)) return json({ error: "valid_upload_id_required" }, 400);

  const admin = createClient(url, secret, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data: upload, error: uploadError } = await admin.from("upload_records").select("*").eq("id", uploadId).maybeSingle();
  if (uploadError || !upload) return json({ error: "upload_not_found" }, 404);

  const { data: profile } = await admin.from("profiles").select("role").eq("id", authData.user.id).maybeSingle();
  let authorized = upload.uploaded_by === authData.user.id || ["owner","admin"].includes(profile?.role ?? "");
  if (!authorized && upload.case_id && ["analyst","reviewer"].includes(profile?.role ?? "")) {
    const { data: assignment } = await admin.from("case_assignments").select("id").eq("case_id", upload.case_id)
      .eq("staff_user_id", authData.user.id).eq("active", true).limit(1).maybeSingle();
    authorized = !!assignment;
  }
  if (!authorized) return json({ error: "upload_processing_not_authorized" }, 403);
  if (upload.source_id) return json({ ok: true, state: "already_registered", source_id: upload.source_id });

  const { data: job, error: jobError } = await admin.from("record_intake_jobs").select("*").eq("upload_id", uploadId).maybeSingle();
  if (jobError || !job) return json({ error: "intake_job_not_found" }, 409);

  // @ts-ignore Supabase Edge Runtime global
  EdgeRuntime.waitUntil(processUpload(admin, upload as Upload, job as Job));
  return json({ ok: true, state: "queued", upload_id: uploadId, processor_version: PROCESSOR_VERSION }, 202);
});
