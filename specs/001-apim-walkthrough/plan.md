# Implementation Plan: APIM walkthrough

Feature directory: `001-apim-walkthrough`. Input: [spec.md](spec.md).
Prepared using the installed Spec Kit planning scaffold and approved user choices.

## Summary

Prepare live Standard v2 APIM with the complete Weather.gov API and independent
developer, security, monitoring, MCP, and AI segments. Keep deployment out of
the presentation. Use Bicep/AZD and a synthetic protection lab.

## Technical Context

- Python 3.12 in a VS Code DevContainer; CFS dependencies in requirements.lock.
- APIM StandardV2, Log Analytics, workspace-based Application Insights.
- Jupyter, current MCP/OpenAI SDK APIs, async Azure CLI credentials.
- No application database, hosted agent, VNet, or new model deployment.
- Tests: unittest, notebook validation, OpenAPI validation, Bicep build.
- Scope: seeded developer, second-account signup, three MCP tools, existing model.
- Bounds: three model turns, one tool per turn, request time/context limits.

## Constitution Check

Design passes: container-only tools, CFS, live public data, independent modules,
simple scoped access, declarative baseline, and explicit human deployment.
Local validation and live acceptance are separate gates, not assumed results.

## Phase 0: Research

See [research.md](research.md): complete import, MCP preview schema, default
portal, telemetry delay, SDK compatibility, and CFS package availability.

## Phase 1: Design

See [data-model.md](data-model.md), [contracts/modules.md](contracts/modules.md),
and [quickstart.md](quickstart.md). No unresolved scope decisions.
Fresh Azure runtime behavior remains a live acceptance gate.

## Project Structure

```text
.devcontainer/       local-only image and CFS configuration
.specify/            installed workflow and constitution
api/                 complete contract and inventory
infra/               Bicep baseline and operational seed templates
policies/            policies and reusable fragments
scripts/             shared helpers, preparation, seeding, notebook generation
notebooks/           presenter notebook
docs/                setup, atomic modules, runbook, troubleshooting
tests/               focused contract/helper/notebook tests
```

## Complexity Tracking

Small direct Bicep resources keep policy/MCP teaching surfaces visible without
external module restores. No separate application platform or infrastructure
framework is introduced.
