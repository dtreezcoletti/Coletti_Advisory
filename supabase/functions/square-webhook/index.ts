type JsonRecord = Record<string, any>;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function parseNamedKey(envName: string, fallbackName: string): string {
  const raw = Deno.env.get(envName);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (typeof parsed?.default === "string" && parsed.default) return parsed.default;
    } catch {
      // Fall through to legacy fallback.
    }
  }
  return Deno.env.get(fallbackName) ?? "";
}

function secretKey(): string {
  return parseNamedKey("SUPABASE_SECRET_KEYS", "SUPABASE_SERVICE_ROLE_KEY");
}

function adminHeaders(extra: HeadersInit = {}): HeadersInit {
  const key = secretKey();
  const headers: Record<string, string> = {
    apikey: key,
    "content-type": "application/json",
  };
  if (!key.startsWith("sb_secret_")) headers.authorization = `Bearer ${key}`;
  return { ...headers, ...(extra as Record<string, string>) };
}

async function fetchJson(url: string, init: RequestInit): Promise<{ response: Response; body: any }> {
  const response = await fetch(url, init);
  let body: any = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return { response, body };
}

function restUrl(path: string): string {
  return `${Deno.env.get("SUPABASE_URL")}/rest/v1/${path}`;
}

function constantTimeEqual(a: string, b: string): boolean {
  const length = Math.max(a.length, b.length);
  let diff = a.length ^ b.length;
  for (let i = 0; i < length; i += 1) {
    diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }
  return diff === 0;
}

async function squareSignature(rawBody: string, notificationUrl: string, signatureKey: string): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(signatureKey),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const digest = await crypto.subtle.sign(
    "HMAC",
    key,
    encoder.encode(notificationUrl + rawBody),
  );
  const bytes = new Uint8Array(digest);
  return btoa(String.fromCharCode(...bytes));
}

function paymentStatus(squareStatus: string): string {
  switch ((squareStatus ?? "").toUpperCase()) {
    case "COMPLETED":
      return "SUCCEEDED";
    case "FAILED":
    case "CANCELED":
      return "FAILED";
    case "APPROVED":
    case "PENDING":
    default:
      return "PENDING";
  }
}

function refundStatus(squareStatus: string): string {
  switch ((squareStatus ?? "").toUpperCase()) {
    case "COMPLETED":
      return "SUCCEEDED";
    case "FAILED":
    case "REJECTED":
      return "FAILED";
    case "PENDING":
    default:
      return "PENDING";
  }
}

async function eventState(eventId: string): Promise<string | null> {
  const result = await fetchJson(
    restUrl(
      `payment_provider_events?provider=eq.square&event_id=eq.${encodeURIComponent(eventId)}&select=processing_status&limit=1`,
    ),
    { method: "GET", headers: adminHeaders() },
  );
  if (!result.response.ok) throw new Error("payment event lookup failed");
  return result.body?.[0]?.processing_status ?? null;
}

async function markEvent(eventId: string, patch: JsonRecord): Promise<void> {
  const result = await fetchJson(
    restUrl(
      `payment_provider_events?provider=eq.square&event_id=eq.${encodeURIComponent(eventId)}`,
    ),
    {
      method: "PATCH",
      headers: adminHeaders({ prefer: "return=minimal" }),
      body: JSON.stringify(patch),
    },
  );
  if (!result.response.ok) throw new Error("payment event update failed");
}

async function findInvoiceByOrder(orderId: string): Promise<any | null> {
  const result = await fetchJson(
    restUrl(
      `invoices?provider=eq.square&provider_order_id=eq.${encodeURIComponent(orderId)}&select=id,amount_cents,status&limit=1`,
    ),
    { method: "GET", headers: adminHeaders() },
  );
  if (!result.response.ok) throw new Error("invoice lookup failed");
  return result.body?.[0] ?? null;
}

async function processPayment(eventId: string, payment: JsonRecord): Promise<void> {
  const providerPaymentId = String(payment?.id ?? "");
  const orderId = String(payment?.order_id ?? "");
  if (!providerPaymentId || !orderId) {
    await markEvent(eventId, {
      processing_status: "IGNORED",
      processed_at: new Date().toISOString(),
      error_message: "Square payment event did not include payment.id and order_id.",
    });
    return;
  }

  const invoice = await findInvoiceByOrder(orderId);
  if (!invoice) {
    await markEvent(eventId, {
      processing_status: "IGNORED",
      processed_at: new Date().toISOString(),
      error_message: "Square order is not linked to a Coletti invoice.",
    });
    return;
  }

  const amount = Number(payment?.amount_money?.amount ?? 0);
  if (!Number.isSafeInteger(amount) || amount < 0) {
    throw new Error("Square payment amount is invalid");
  }

  const mappedStatus = paymentStatus(String(payment?.status ?? ""));
  const paidAt =
    mappedStatus === "SUCCEEDED"
      ? String(payment?.updated_at ?? payment?.created_at ?? new Date().toISOString())
      : null;

  const upsert = await fetchJson(
    restUrl("payments?on_conflict=provider,provider_payment_id"),
    {
      method: "POST",
      headers: adminHeaders({
        prefer: "resolution=merge-duplicates,return=representation",
      }),
      body: JSON.stringify({
        invoice_id: invoice.id,
        amount_cents: amount,
        status: mappedStatus,
        provider: "square",
        provider_payment_id: providerPaymentId,
        provider_order_id: orderId,
        paid_at: paidAt,
        updated_at: new Date().toISOString(),
      }),
    },
  );
  if (!upsert.response.ok) {
    console.error("Square payment upsert failed", upsert.response.status, upsert.body);
    throw new Error("payment upsert failed");
  }

  if (mappedStatus === "SUCCEEDED") {
    const successful = await fetchJson(
      restUrl(
        `payments?invoice_id=eq.${encodeURIComponent(invoice.id)}&status=eq.SUCCEEDED&select=amount_cents`,
      ),
      { method: "GET", headers: adminHeaders() },
    );
    if (!successful.response.ok) throw new Error("successful payment total lookup failed");

    const totalPaid = (successful.body ?? []).reduce(
      (sum: number, row: any) => sum + Number(row.amount_cents ?? 0),
      0,
    );

    if (totalPaid >= Number(invoice.amount_cents)) {
      const invoiceUpdate = await fetchJson(
        restUrl(`invoices?id=eq.${encodeURIComponent(invoice.id)}`),
        {
          method: "PATCH",
          headers: adminHeaders({ prefer: "return=minimal" }),
          body: JSON.stringify({
            status: "PAID",
            updated_at: new Date().toISOString(),
          }),
        },
      );
      if (!invoiceUpdate.response.ok) throw new Error("invoice paid-state update failed");
    }
  }

  await markEvent(eventId, {
    processing_status: "PROCESSED",
    processed_at: new Date().toISOString(),
    error_message: null,
  });
}

async function processRefund(eventId: string, refund: JsonRecord): Promise<void> {
  const providerRefundId = String(refund?.id ?? "");
  const providerPaymentId = String(refund?.payment_id ?? "");
  if (!providerRefundId || !providerPaymentId) {
    await markEvent(eventId, {
      processing_status: "IGNORED",
      processed_at: new Date().toISOString(),
      error_message: "Square refund event did not include refund.id and payment_id.",
    });
    return;
  }

  const paymentResult = await fetchJson(
    restUrl(
      `payments?provider=eq.square&provider_payment_id=eq.${encodeURIComponent(providerPaymentId)}&select=id,amount_cents,status&limit=1`,
    ),
    { method: "GET", headers: adminHeaders() },
  );
  if (!paymentResult.response.ok) throw new Error("parent payment lookup failed");
  const parent = paymentResult.body?.[0];
  if (!parent) {
    await markEvent(eventId, {
      processing_status: "IGNORED",
      processed_at: new Date().toISOString(),
      error_message: "Square refund is not linked to a recorded Coletti payment.",
    });
    return;
  }

  const amount = Number(refund?.amount_money?.amount ?? 0);
  if (!Number.isSafeInteger(amount) || amount < 0) {
    throw new Error("Square refund amount is invalid");
  }

  const mappedStatus = refundStatus(String(refund?.status ?? ""));
  const refundedAt =
    mappedStatus === "SUCCEEDED"
      ? String(refund?.updated_at ?? refund?.created_at ?? new Date().toISOString())
      : null;

  const upsert = await fetchJson(
    restUrl("payment_refunds?on_conflict=provider,provider_refund_id"),
    {
      method: "POST",
      headers: adminHeaders({
        prefer: "resolution=merge-duplicates,return=representation",
      }),
      body: JSON.stringify({
        payment_id: parent.id,
        amount_cents: amount,
        status: mappedStatus,
        provider: "square",
        provider_refund_id: providerRefundId,
        refunded_at: refundedAt,
        updated_at: new Date().toISOString(),
      }),
    },
  );
  if (!upsert.response.ok) {
    console.error("Square refund upsert failed", upsert.response.status, upsert.body);
    throw new Error("refund upsert failed");
  }

  const successfulRefunds = await fetchJson(
    restUrl(
      `payment_refunds?payment_id=eq.${encodeURIComponent(parent.id)}&status=eq.SUCCEEDED&select=amount_cents`,
    ),
    { method: "GET", headers: adminHeaders() },
  );
  if (!successfulRefunds.response.ok) throw new Error("refund total lookup failed");

  const refunded = (successfulRefunds.body ?? []).reduce(
    (sum: number, row: any) => sum + Number(row.amount_cents ?? 0),
    0,
  );

  if (refunded > 0) {
    const parentStatus =
      refunded >= Number(parent.amount_cents) ? "REFUNDED" : "PARTIALLY_REFUNDED";
    const updateParent = await fetchJson(
      restUrl(`payments?id=eq.${encodeURIComponent(parent.id)}`),
      {
        method: "PATCH",
        headers: adminHeaders({ prefer: "return=minimal" }),
        body: JSON.stringify({
          status: parentStatus,
          updated_at: new Date().toISOString(),
        }),
      },
    );
    if (!updateParent.response.ok) throw new Error("payment refund-state update failed");
  }

  await markEvent(eventId, {
    processing_status: "PROCESSED",
    processed_at: new Date().toISOString(),
    error_message: null,
  });
}


function bookingEventState(eventType: string, squareStatus: string): string {
  const status = (squareStatus ?? "").toUpperCase();
  if (status === "CANCELLED_BY_CUSTOMER" || status === "CANCELLED_BY_SELLER" || status === "DECLINED") {
    return "CANCELLED";
  }
  if (status === "NO_SHOW") return "COMPLETED";
  if (eventType === "booking.created") {
    return status === "ACCEPTED" ? "CONFIRMED" : "BOOKED";
  }
  return "UPDATED";
}

function bookingEndAt(booking: JsonRecord): string {
  const startAt = String(booking?.start_at ?? "");
  const start = Date.parse(startAt);
  if (!startAt || Number.isNaN(start)) throw new Error("Square booking start_at is invalid");

  const segmentMinutes = Array.isArray(booking?.appointment_segments)
    ? booking.appointment_segments.reduce(
        (sum: number, segment: any) => sum + Number(segment?.duration_minutes ?? 0),
        0,
      )
    : 0;
  const transitionMinutes = Number(booking?.transition_time_minutes ?? 0);
  const totalMinutes = segmentMinutes + transitionMinutes;

  if (!Number.isFinite(totalMinutes) || totalMinutes <= 0) {
    throw new Error("Square booking duration is invalid");
  }
  return new Date(start + totalMinutes * 60_000).toISOString();
}

async function processBooking(eventId: string, eventType: string, booking: JsonRecord): Promise<void> {
  const bookingId = String(booking?.id ?? "");
  const startAt = String(booking?.start_at ?? "");
  if (!bookingId || !startAt) {
    await markEvent(eventId, {
      processing_status: "IGNORED",
      processed_at: new Date().toISOString(),
      error_message: "Square booking event did not include booking.id and start_at.",
    });
    return;
  }

  const mappedState = bookingEventState(eventType, String(booking?.status ?? ""));
  const endAt = bookingEndAt(booking);
  const firstSegment = Array.isArray(booking?.appointment_segments)
    ? booking.appointment_segments[0] ?? {}
    : {};
  const timezone = Deno.env.get("COLETTI_TIMEZONE") ?? "America/Chicago";

  const rpc = await fetchJson(
    `${Deno.env.get("SUPABASE_URL")}/rest/v1/rpc/square_consultation_event_v1`,
    {
      method: "POST",
      headers: adminHeaders(),
      body: JSON.stringify({
        p_provider_booking_id: bookingId,
        p_event_type: mappedState,
        p_start_at: mappedState === "CANCELLED" ? null : startAt,
        p_end_at: mappedState === "CANCELLED" ? null : endAt,
        p_timezone: timezone,
        p_google_event_id: null,
        p_payment_state: null,
        p_service_key: String(firstSegment?.service_variation_id ?? "") || null,
        p_client_ref: String(booking?.customer_id ?? "") || null,
        p_payload: {
          square_event_id: eventId,
          square_event_type: eventType,
          square_status: String(booking?.status ?? ""),
          booking_version: booking?.version ?? null,
          location_id: booking?.location_id ?? null,
          service_variation_ids: Array.isArray(booking?.appointment_segments)
            ? booking.appointment_segments
                .map((segment: any) => String(segment?.service_variation_id ?? ""))
                .filter(Boolean)
            : [],
        },
      }),
    },
  );

  if (!rpc.response.ok) {
    console.error("Square booking reconciliation RPC failed", rpc.response.status, rpc.body);
    throw new Error("booking reconciliation rpc failed");
  }

  await markEvent(eventId, {
    processing_status: "PROCESSED",
    processed_at: new Date().toISOString(),
    error_message: null,
  });
}

Deno.serve(async (request) => {
  if (request.method !== "POST") return jsonResponse({ error: "method_not_allowed" }, 405);

  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const serviceKey = secretKey();
  const webhookUrl = Deno.env.get("SQUARE_WEBHOOK_URL") ?? "";
  const webhookSignatureKey = Deno.env.get("SQUARE_WEBHOOK_SIGNATURE_KEY") ?? "";

  if (!supabaseUrl || !serviceKey || !webhookUrl || !webhookSignatureKey) {
    return jsonResponse({ error: "webhook_not_configured" }, 503);
  }

  const rawBody = await request.text();
  const suppliedSignature = request.headers.get("x-square-hmacsha256-signature") ?? "";
  const expectedSignature = await squareSignature(
    rawBody,
    webhookUrl,
    webhookSignatureKey,
  );

  if (!suppliedSignature || !constantTimeEqual(suppliedSignature, expectedSignature)) {
    return jsonResponse({ error: "invalid_signature" }, 401);
  }

  let event: JsonRecord;
  try {
    event = JSON.parse(rawBody);
  } catch {
    return jsonResponse({ error: "invalid_json" }, 400);
  }

  const eventId = String(event?.event_id ?? "");
  const eventType = String(event?.type ?? "");
  if (!eventId || !eventType) {
    return jsonResponse({ error: "event_id_and_type_required" }, 400);
  }

  const payment = event?.data?.object?.payment;
  const refund = event?.data?.object?.refund;
  const booking = event?.data?.object?.booking;
  const object = payment ?? refund ?? booking ?? {};
  const objectId = String(object?.id ?? "") || null;
  const orderId = String(payment?.order_id ?? "") || null;
  const providerStatus = String(object?.status ?? "") || null;

  const insert = await fetchJson(restUrl("payment_provider_events"), {
    method: "POST",
    headers: adminHeaders({ prefer: "return=minimal" }),
    body: JSON.stringify({
      provider: "square",
      event_id: eventId,
      event_type: eventType,
      object_id: objectId,
      provider_order_id: orderId,
      provider_status: providerStatus,
      event_version: event?.version ? String(event.version) : null,
      processing_status: "RECEIVED",
    }),
  });

  if (!insert.response.ok) {
    const duplicate = insert.response.status === 409 || insert.body?.code === "23505";
    if (!duplicate) {
      console.error("Square event ledger insert failed", insert.response.status, insert.body);
      return jsonResponse({ error: "event_ledger_failed" }, 500);
    }
    const existingState = await eventState(eventId);
    if (existingState === "PROCESSED" || existingState === "IGNORED") {
      return jsonResponse({ ok: true, duplicate: true });
    }
  }

  try {
    if (eventType === "payment.created" || eventType === "payment.updated") {
      if (!payment) throw new Error("payment event missing payment object");
      await processPayment(eventId, payment);
    } else if (eventType === "refund.created" || eventType === "refund.updated") {
      if (!refund) throw new Error("refund event missing refund object");
      await processRefund(eventId, refund);
    } else if (eventType === "booking.created" || eventType === "booking.updated") {
      if (!booking) throw new Error("booking event missing booking object");
      await processBooking(eventId, eventType, booking);
    } else {
      await markEvent(eventId, {
        processing_status: "IGNORED",
        processed_at: new Date().toISOString(),
        error_message: "Webhook event type is not used by Coletti Billing or consultation scheduling.",
      });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "unknown processing failure";
    console.error("Square webhook processing failed", eventId, eventType, message);
    try {
      await markEvent(eventId, {
        processing_status: "FAILED",
        processed_at: new Date().toISOString(),
        error_message: message.slice(0, 1000),
      });
    } catch (ledgerError) {
      console.error("Unable to record Square webhook failure", ledgerError);
    }
    return jsonResponse({ error: "processing_failed" }, 500);
  }

  return jsonResponse({ ok: true });
});
