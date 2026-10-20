/**
 * ColettiOS staging-only MCP Owner identity proof.
 *
 * No mutation tools and no implied Dispatcher/Executive Executor authority.
 * Never use the Supabase service-role key in this component.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { createRemoteJWKSet, jwtVerify } from "jose";

interface Env {
  DEPLOYMENT_STAGE: string;
  SUPABASE_URL: string;
  SUPABASE_PUBLISHABLE_KEY: string;
  MCP_RESOURCE_URL: string;
  EXPECTED_OWNER_SUB: string;
  ALLOWED_OAUTH_CLIENT_ID: string;
}

class AuthorizationError extends Error {
  constructor(public readonly status: 401 | 403 | 503, message: string) {
    super(message);
  }
}

function json(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
      ...headers,
    },
  });
}

function requireConfiguration(env: Env): void {
  const required = [
    env.SUPABASE_URL,
    env.SUPABASE_PUBLISHABLE_KEY,
    env.MCP_RESOURCE_URL,
    env.EXPECTED_OWNER_SUB,
    env.ALLOWED_OAUTH_CLIENT_ID,
  ];
  if (env.DEPLOYMENT_STAGE !== "staging" || required.some(v => !v?.trim())) {
    throw new AuthorizationError(503, "Staging OAuth configuration incomplete");
  }
  if (!env.MCP_RESOURCE_URL.startsWith("https://") ||
      !env.MCP_RESOURCE_URL.endsWith("/mcp") ||
      !env.SUPABASE_URL.startsWith("https://") ||
      env.SUPABASE_URL.endsWith("/")) {
    throw new AuthorizationError(503, "Invalid staging OAuth endpoint configuration");
  }
  try {
    const auth = new URL(env.SUPABASE_URL);
    const resource = new URL(env.MCP_RESOURCE_URL);
    if (auth.protocol !== "https:" || resource.protocol !== "https:") {
      throw new Error("HTTPS required");
    }
  } catch {
    throw new AuthorizationError(503, "Invalid OAuth URL");
  }
}

function authIssuer(env: Env): string {
  return env.SUPABASE_URL + "/auth/v1";
}

function resourceMetadata(env: Env): Response {
  return json({
    resource: env.MCP_RESOURCE_URL,
    authorization_servers: [authIssuer(env)],
    scopes_supported: ["openid", "profile"],
  });
}

function challenge(env: Env, status: 401 | 403 = 401): Response {
  const endpoint = new URL("/.well-known/oauth-protected-resource", env.MCP_RESOURCE_URL);
  const header = 'Bearer resource_metadata="' + endpoint.href + '", error="invalid_token", error_description="Valid ColettiOS Owner authorization is required"';
  return json({ error: "authorization_required" }, status, {
    "www-authenticate": header,
  });
}

function bearerFrom(request: Request): string {
  const authorization = request.headers.get("authorization") || "";
  const matched = authorization.match(/^Bearer ([A-Za-z0-9._~+/-]+=*)$/);
  if (!matched) throw new AuthorizationError(401, "Bearer token missing");
  return matched[1];
}

async function verifyOwner(request: Request, env: Env): Promise<void> {
  const token = bearerFrom(request);
  // OAuth JWTs must use an asymmetric signing key discoverable at JWKS.
  // No symmetric-key fallback, secret leakage, or unverified JWT decoding.
  const jwksUrl = new URL(authIssuer(env) + "/.well-known/jwks.json");
  const jwks = createRemoteJWKSet(jwksUrl);
  let payload;
  try {
    const result = await jwtVerify(token, jwks, {
      issuer: authIssuer(env),
      audience: env.MCP_RESOURCE_URL,
      algorithms: ["ES256", "RS256"],
    });
    payload = result.payload;
  } catch {
    throw new AuthorizationError(401, "Invalid token");
  }

  const subject = payload.sub;
  const clientId = payload.client_id;
  const sessionId = payload.session_id;
  if (typeof subject !== "string" || subject !== env.EXPECTED_OWNER_SUB ||
      typeof clientId !== "string" || clientId !== env.ALLOWED_OAUTH_CLIENT_ID ||
      typeof sessionId !== "string" || sessionId.length === 0) {
    throw new AuthorizationError(403, "Owner identity or OAuth client mismatch");
  }

  const scope = typeof payload.scope === "string" ? payload.scope.split(/\s+/) : [];
  if (!scope.includes("openid")) {
    throw new AuthorizationError(403, "Missing required OAuth scope");
  }

  // Run profile validation with the *same* user token and publishable key.
  // Supabase RLS is enforced; no backend service-role bypass.
  const profileUrl = new URL(env.SUPABASE_URL + "/rest/v1/profiles");
  profileUrl.searchParams.set("select", "id,role,status");
  profileUrl.searchParams.set("id", "eq." + subject);

  let response: Response;
  try {
    response = await fetch(profileUrl, {
      headers: {
        "apikey": env.SUPABASE_PUBLISHABLE_KEY,
        "authorization": "Bearer " + token,
        "accept": "application/json",
      },
      method: "GET",
      redirect: "error",
    });
  } catch {
    throw new AuthorizationError(503, "Owner profile service unavailable");
  }

  if (!response.ok) {
    throw new AuthorizationError(503, "Owner profile could not be verified");
  }

  const profiles: unknown = await response.json().catch(() => null);
  if (!Array.isArray(profiles) || profiles.length !== 1) {
    throw new AuthorizationError(403, "Owner profile unavailable");
  }
  const profile = profiles[0] as Record<string, unknown>;
  if (profile.id !== subject || profile.role !== "owner" || profile.status !== "ACTIVE") {
    throw new AuthorizationError(403, "Active Owner profile required");
  }
}

async function serveMcp(request: Request): Promise<Response> {
  // New server and transport per request prevent cross-user state bleed.
  const server = new McpServer({ name: "colettios-owner-staging", version: "0.1.0" });
  server.registerTool(
    "verify_colettios_owner",
    {
      title: "Verify ColettiOS Owner",
      description: "Verify an authorized, authenticated Owner identity; never grants execution or changes ColettiOS.",
      inputSchema: {},
      securitySchemes: [{ type: "oauth2", scopes: ["openid", "profile"] }],
      annotations: { readOnlyHint: true, destructiveHint: false },
    },
    async () => ({
      content: [{
        type: "text",
        text: JSON.stringify({
          owner_authentication: "verified",
          environment: "staging",
          execution_authority: "not_granted",
          worker_commissioning: "not_started",
        }),
      }],
    }),
  );
  const transport = new WebStandardStreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
  });
  await server.connect(transport);
  return transport.handleRequest(request);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    try {
      requireConfiguration(env);
      const url = new URL(request.url);
      const resource = new URL(env.MCP_RESOURCE_URL);
      const authMetadataPath = "/.well-known/oauth-protected-resource";

      if (request.method === "GET" &&
          (url.pathname === authMetadataPath ||
           url.pathname === authMetadataPath + resource.pathname)) {
        return resourceMetadata(env);
      }
      if (url.pathname === "/health" && request.method === "GET") {
        return json({ service: "colettios-owner-mcp", mode: "staging", writes_enabled: false });
      }

      // Do not accept a different public endpoint or downgrade to plain HTTP.
      if (url.origin !== resource.origin || url.pathname !== resource.pathname) {
        return json({ error: "not_found" }, 404);
      }
      // Only a token that belongs to this resource and exact Owner may reach MCP.
      await verifyOwner(request, env);
      if (request.method !== "POST") {
        return json({ error: "method_not_allowed" }, 405);
      }
      return await serveMcp(request);
    } catch (error) {
      if (error instanceof AuthorizationError) {
        if (error.status === 503) {
          return json({ error: "staging_unavailable" }, 503);
        }
        return challenge(env, error.status);
      }
      return json({ error: "gateway_unavailable" }, 503);
    }
  },
};
