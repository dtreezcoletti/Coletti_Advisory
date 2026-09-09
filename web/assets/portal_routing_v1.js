import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.115.0/+esm';
import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY } from './config.js';

/*
 * Role-aware authenticated routing guard.
 *
 * The operational frontend uses one canonical host and hash-based routes. This
 * guard prevents authenticated staff/owner identities from being stranded in
 * client-only portal routes after a passwordless sign-in callback.
 *
 * It does not create identity or authorization. Supabase Auth and the existing
 * profile/RLS controls remain authoritative; this module only chooses the
 * correct UI landing surface after authentication.
 */

const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
});

const ADMIN_ROLES = new Set(['owner', 'admin']);
const STAFF_ROLES = new Set(['owner', 'admin', 'analyst', 'reviewer']);
let routing = false;

function currentRoute() {
  return (location.hash || '#/home').replace(/^#/, '');
}

function routeForRole(role) {
  if (ADMIN_ROLES.has(role)) return '/admin/home';
  if (STAFF_ROLES.has(role)) return '/workspace/home';
  return '/portal/home';
}

async function authenticatedRole() {
  const { data: sessionData } = await supabase.auth.getSession();
  const user = sessionData?.session?.user;
  if (!user) return null;

  const { data: profile, error } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .maybeSingle();

  if (error) {
    console.error('Portal routing profile lookup failed', error);
    return null;
  }
  return profile?.role || 'client';
}

async function enforceRoleAwareLanding() {
  if (routing) return;
  routing = true;
  try {
    const role = await authenticatedRole();
    if (!role) return;

    const route = currentRoute();
    const landing = routeForRole(role);

    // Sign-in is a transient route once a session exists.
    if (route === '/sign-in') {
      if (route !== landing) location.hash = `#${landing}`;
      return;
    }

    // Staff identities must never remain on a client-only portal route after
    // a magic-link callback. Owners/admins land in the command center;
    // analysts/reviewers land in the operations workspace.
    if (route.startsWith('/portal/') && STAFF_ROLES.has(role)) {
      location.hash = `#${landing}`;
    }
  } finally {
    routing = false;
  }
}

window.addEventListener('hashchange', () => void enforceRoleAwareLanding());
window.addEventListener('DOMContentLoaded', () => void enforceRoleAwareLanding());
supabase.auth.onAuthStateChange(() => queueMicrotask(() => void enforceRoleAwareLanding()));
queueMicrotask(() => void enforceRoleAwareLanding());
