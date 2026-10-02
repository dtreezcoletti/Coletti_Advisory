const SQUARE_VERSION = "2026-09-16";

type InvoiceRow = {
  id: string;
  case_id: string | null;
  client_user_id: string;
  invoice_number: string;
  amount_cents: number | string;
  status: string;
  provider: string | null;
  payment_url: string | null;
  provider_order_id: string | null;
  provider_payment_link_id: string | null;
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
    },
  });
}

function parseNamedKey(envName: string, fallbackName: string): string {
  const raw = Deno.env.get(envName);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (typeof parsed?.default === "string" && parsed.default) return parsed.default;
    } catch {
      // Ignore malformed JSON here and fall through to the explicit fallback.
    }
  }
  return Deno.env.get(fallbackName) ?? "";
}

function publishableKey(): string {
  return parseNamedKey("SUPABASE_PUBLISHABLE_KEYS", "SUPABASE_ANON_KEY");
}

function bearerToken(request: Request): string {
  const authorization = request.headers.get("authorization") ?? "";
  if (!authorization.startsWith("Bearer ")) return "";
  return authorization.slice("Bearer ".length).trim();
}

function userHeaders(jwt: string): HeadersInit {
  const key = publishableKey();
  return {
    apikey: key,
    authorization: `Bearer ${jwt}`,
    "content-type": "application/json",
  };
}

function squareBaseUrl(): string {
  const environment = (Deno.env.get("SQUARE_ENVIRONMENT") ?? "").toLowerCase();
  if (environment === "production") return "https://connect.squareup.com";
  if (environment === "sandbox") return "https://connect.squareupsandbox.com";
  return "";
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

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "access-control-allow-origin": "*",
        "access-control-allow-headers": "authorization, x-client-info, apikey, content-type",
        "access-control-allow-methods": "POST, OPTIONS",
      },
    });
  }

  if (request.method !== "POST") return jsonResponse({ error: "method_not_allowed" }, 405);

  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const publicKey = publishableKey();
  const jwt = bearerToken(request);
  if (!supabaseUrl || !publicKey) return jsonResponse({ error: "supabase_not_configured" }, 503);
  if (!jwt) return jsonResponse({ error: "authentication_required" }, 401);

  let requestBody: { invoice_id?: string };
  try {
    requestBody = await request.json();
  } catch {
    return jsonResponse({ error: "invalid_json" }, 400);
  }

  const invoiceId = (requestBody.invoice_id ?? "").trim();
  if (!/^[0-9a-f-]{36}$/i.test(invoiceId)) {
    return jsonResponse({ error: "valid_invoice_id_required" }, 400);
  }

  const auth = await fetchJson(`${supabaseUrl}/auth/v1/user`, {
    method: "GET",
    headers: userHeaders(jwt),
  });
  if (!auth.response.ok || !auth.body?.id) {
    return jsonResponse({ error: "invalid_session" }, 401);
  }

  const profile = await fetchJson(
    `${supabaseUrl}/rest/v1/profiles?id=eq.${encodeURIComponent(auth.body.id)}&select=id,role&limit=1`,
    { method: "GET", headers: userHeaders(jwt) },
  );
  const role = profile.body?.[0]?.role;
  if (!profile.response.ok || !["owner", "admin"].includes(role)) {
    return jsonResponse({ error: "billing_authority_required" }, 403);
  }

  const invoiceResult = await fetchJson(
    `${supabaseUrl}/rest/v1/invoices?id=eq.${encodeURIComponent(invoiceId)}&select=id,case_id,client_user_id,invoice_number,amount_cents,status,provider,payment_url,provider_order_id,provider_payment_link_id&limit=1`,
    { method: "GET", headers: userHeaders(jwt) },
  );
  const invoice = invoiceResult.body?.[0] as InvoiceRow | undefined;
  if (!invoiceResult.response.ok) {
    return jsonResponse({ error: "invoice_lookup_failed" }, 502);
  }
  if (!invoice) return jsonResponse({ error: "invoice_not_found" }, 404);
  if (invoice.status === "PAID" || invoice.status === "VOID") {
    return jsonResponse({ error: "invoice_not_payable", status: invoice.status }, 409);
  }

  if (
    invoice.provider === "square" &&
    invoice.payment_url &&
    invoice.provider_order_id &&
    invoice.provider_payment_link_id
  ) {
    return jsonResponse({
      invoice_id: invoice.id,
      payment_url: invoice.payment_url,
      provider: "square",
      reused: true,
    });
  }

  const squareToken = Deno.env.get("SQUARE_ACCESS_TOKEN") ?? "";
  const squareLocationId = Deno.env.get("SQUARE_LOCATION_ID") ?? "";
  const squareBase = squareBaseUrl();
  if (!squareToken || !squareLocationId || !squareBase) {
    return jsonResponse({ error: "square_not_configured" }, 503);
  }

  const amount = Number(invoice.amount_cents);
  if (!Number.isSafeInteger(amount) || amount <= 0) {
    return jsonResponse({ error: "invoice_amount_invalid" }, 409);
  }

  const returnUrl = (Deno.env.get("SQUARE_RETURN_URL") ?? "").trim();
  const squareRequest: Record<string, unknown> = {
    idempotency_key: `coletti-invoice-${invoice.id}-v1`,
    description: `Coletti & Co. invoice ${invoice.invoice_number}`,
    order: {
      location_id: squareLocationId,
      reference_id: invoice.id,
      line_items: [
        {
          name: `Coletti & Co. invoice ${invoice.invoice_number}`,
          quantity: "1",
          base_price_money: { amount, currency: "USD" },
        },
      ],
    },
    payment_note: `Coletti & Co. invoice ${invoice.invoice_number}`,
  };
  if (returnUrl) squareRequest.checkout_options = { redirect_url: returnUrl };

  const square = await fetchJson(`${squareBase}/v2/online-checkout/payment-links`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${squareToken}`,
      "content-type": "application/json",
      "square-version": SQUARE_VERSION,
    },
    body: JSON.stringify(squareRequest),
  });

  if (!square.response.ok) {
    console.error("Square payment-link request failed", square.response.status, square.body?.errors ?? null);
    return jsonResponse(
      {
        error: "square_payment_link_failed",
        provider_status: square.response.status,
      },
      502,
    );
  }

  const link = square.body?.payment_link;
  if (!link?.id || !link?.order_id || !link?.url) {
    console.error("Square payment-link response was incomplete", square.body);
    return jsonResponse({ error: "square_payment_link_incomplete" }, 502);
  }

  const update = await fetchJson(
    `${supabaseUrl}/rest/v1/invoices?id=eq.${encodeURIComponent(invoice.id)}`,
    {
      method: "PATCH",
      headers: {
        ...userHeaders(jwt),
        prefer: "return=representation",
      },
      body: JSON.stringify({
        provider: "square",
        provider_order_id: link.order_id,
        provider_payment_link_id: link.id,
        payment_url: link.url,
        status: "OPEN",
        updated_at: new Date().toISOString(),
      }),
    },
  );

  if (!update.response.ok) {
    console.error("Invoice update failed after Square link creation", update.response.status, update.body);
    return jsonResponse(
      {
        error: "invoice_update_failed_after_provider_creation",
        provider_payment_link_id: link.id,
      },
      502,
    );
  }

  return jsonResponse({
    invoice_id: invoice.id,
    invoice_number: invoice.invoice_number,
    provider: "square",
    provider_order_id: link.order_id,
    provider_payment_link_id: link.id,
    payment_url: link.url,
    reused: false,
  });
});
