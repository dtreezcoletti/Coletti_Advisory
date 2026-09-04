# Coletti & Co.

Coletti & Co. is the commercial implementation layer that uses released ColettiOS capabilities to perform defined record-analysis and operational-reconstruction services for future clients.

## Boundary

This repository is **not** the ColettiOS core repository and must not contain private historical case facts, real-case demonstrations, settlement information, personal evidentiary source material, or hard-coded client assumptions.

Commercial code should consume generalized ColettiOS interfaces and add only:

- service definitions;
- intake and client-workspace logic;
- contracts and scope controls;
- report presentation;
- engagement operations;
- client-specific configuration stored outside reusable source code.

## Marketing firewall

Historical matters may teach methodology, but public demonstrations must use synthetic data only.

`historical lesson -> generalized ColettiOS rule -> synthetic demonstration -> Coletti & Co. service`

## Current migration status

This repository contains legacy modules from an earlier case-driven build. Those modules are being reviewed and generalized. Real-case constants are not considered approved commercial architecture.

See `PROJECT_BOUNDARY.md` and `MIGRATION_REGISTER.md`.
