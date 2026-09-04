# Coletti & Co. Project Boundary

Status: CONTROLLED
Effective date: 2026-09-04

## Role

Coletti & Co. is the commercial layer. It packages services, manages engagements, handles intake, and presents outputs generated through released ColettiOS interfaces.

## Service/core separation rule

Coletti & Co. owns the service definition, engagement workflow, client-facing controls, reporting presentation, contracts, operating procedures, and billing/administrative processes.

ColettiOS owns reusable evidence/provenance methodology, evidence-state logic, reconciliation logic, contradiction handling, audit/provenance mechanics, generalized processing rules, and other reusable core capabilities.

The commercial repository may call released ColettiOS functionality through a defined adapter or service contract. It may not duplicate, fork, or silently re-implement reusable ColettiOS core logic as commercial application code.

## Allowed here

- service definitions and scope controls;
- engagement intake schemas;
- client workspace and authentication logic;
- reporting templates and presentation adapters;
- contracts, operating procedures, and billing workflows;
- synthetic demonstrations;
- adapters that call released ColettiOS functionality.

## Not allowed here

- reusable ColettiOS core logic that belongs in the core repository;
- real historical case facts used as source-code constants;
- real party names, case numbers, settlement terms, or evidentiary narratives;
- private source documents;
- public demonstration data copied from a real engagement;
- a system-generated legal, accounting, tax, investigative, or professional conclusion presented as if Coletti & Co. itself made the licensed determination.

## Real-client/default prohibition

Client-specific or historical facts may enter only through an engagement-specific configuration or data layer. They may never become reusable source-code defaults, example constants, built-in demo content, test fixtures derived from a real engagement, or fallback values used when engagement data is absent.

Synthetic fixtures are the only approved built-in/default engagement data.

## Historical-material rule

Historical case material is migration debt and methodology provenance only. It is not approved commercial architecture. Any workflow, rule, model, or interface derived from historical work must be generalized, stripped of case facts, and proven on unrelated synthetic data before it can be treated as reusable product architecture.

## Engagement principle

Client-specific facts enter through an engagement configuration/data layer. They do not become reusable source-code defaults.

## Output principle

Coletti & Co. organizes and reconstructs records, identifies conflicts and gaps, and presents traceable findings about what the records establish. Where a conclusion requires a licensed or professional determination, the output marks that boundary explicitly.
