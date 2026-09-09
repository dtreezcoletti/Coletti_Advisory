# Supabase migrations

This directory is the version-controlled home for Colettico database migrations used by the Supabase GitHub integration.

The production project already contains migration history created before this directory was added. Do not enable automatic production deployment from GitHub until the repository migration history has been reconciled against the production project's `supabase_migrations.schema_migrations` ledger.

New database changes should be created as timestamped SQL migration files in this directory and reviewed before merge to the production branch.
