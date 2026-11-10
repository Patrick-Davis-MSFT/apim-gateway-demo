# APIM Weather Walkthrough Constitution

## Core Principles

### I. Container-only, approved dependencies
Install and execute tools only in the local VS Code DevContainer. Resolve
dependencies through CFS, without fallback or disabled TLS verification.

### II. Live gateway, honest evidence
Run APIM in Azure and preserve the complete Weather.gov operation inventory.
Only the clearly labeled protection probe may be synthetic. Never present
fabricated weather, AI output, or unexecuted live acceptance as verified.

### III. Independent presentation modules
Every module starts from the seeded baseline and its own notebook setup.
Skipping, repeating, or resetting a module must not break another. The fixed
presentation budget is 55 minutes plus a 5-minute discussion buffer.

### IV. Simple security with bounded AI
Use scoped subscriptions, HTTPS, explicit validation and throttling, credential
stripping, safe diagnostics, and existing-model Entra authentication.
Bound and validate AI tools. No hosted agent or complex identity/network setup.

### V. Declarative, repeatable preparation
Use Bicep plus AZD hooks. Complete provisioning, seeding, portal publication,
and telemetry warm-up before presenting. Preserve existing account passwords
and subscription keys. Apply SecurityControl=Ignore to taggable resources.

## Delivery constraints

Documentation is Markdown. Live actions occur in Azure portals or visible
Python notebook cells. Setup commands run only inside the container.
Existing model resources remain externally owned and must not be deleted.

## Quality gates

Validate the container, full API inventory, policy XML, Bicep, helpers, notebooks,
module independence, and secret handling. Separate local checks from live
Azure acceptance. Require explicit human deployment/context selection.

## Governance

Material scope changes need presenter approval. Changes must preserve these
invariants and update related specifications, documentation, and tests.

**Version**: 1.0.0 | **Ratified**: 2026-11-09 | **Last Amended**: 2026-11-09
