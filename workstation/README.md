# ColettiOS Windows Workstation

This package turns a Windows laptop into an authorized **local ColettiOS development/demo workstation** without creating a second ColettiOS codebase.

## Authority model

- `dtreezcoletti/ColettiOS` remains authoritative for ColettiOS Core/IP.
- `dtreezcoletti/Coletti_Advisory` remains authoritative for the Coletti & Co. commercial application.
- Institutional database/state and Dispatcher authority remain in the Colettico Supabase control plane.
- The laptop is an execution node, not the institutional source of truth.

## What the installer does

`Install-ColettiOS.ps1`:

1. verifies Git and Python 3.11/3.12 are available;
2. clones or fast-forward-updates the authoritative ColettiOS and Coletti & Co. repositories;
3. creates isolated Python virtual environments;
4. installs Core/API and commercial dependencies;
5. generates a unique local server-to-server token outside Git;
6. configures the commercial app in `APP_MODE=demo`, `STORAGE_BACKEND=local_demo`, and `COLETTIOS_BACKEND=http`;
7. wires the commercial app to the real private ColettiOS Core service on `127.0.0.1`;
8. stores local Core development state in a workstation SQLite database;
9. runs both repositories' automated test suites;
10. creates a desktop shortcut named **ColettiOS**.

## Launch behavior

The desktop shortcut starts:

- the private ColettiOS Core API on `127.0.0.1:8765`;
- the ColettiOS/Coletti & Co. admin interface on `127.0.0.1:8501`;
- the default browser at the local admin interface.

Both services bind only to localhost in this workstation profile.

## Security boundary

This profile is deliberately **not production**. It is intended for controlled development, synthetic testing, Golden Path work, and local UI use. It must not be treated as authorization to process real-client data.

Production remains separately gated by the existing authentication, authorization, encrypted durable storage, private HTTPS Core service, PostgreSQL persistence, and production acceptance requirements.

## Install

Run PowerShell as the signed-in Windows user:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-ColettiOS.ps1
```

If the private Core clone requests GitHub authentication, complete the GitHub sign-in prompt. No GitHub token is written into the repository by this installer.

## Upgrade

Re-running the installer performs fast-forward updates from the authoritative repositories, rebuilds dependencies, rotates the local-only Core service token, reruns tests, and preserves the local development Core database unless the user explicitly deletes the workstation data directory.
