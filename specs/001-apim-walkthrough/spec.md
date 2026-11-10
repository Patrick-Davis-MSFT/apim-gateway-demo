# Feature Specification: APIM security and developer walkthrough

Status: Approved scope; live acceptance pending.

Input: The user-approved walkthrough plan and clarification responses.
Spec Kit 1.3.2 was initialized from CFS inside the container. Its bundled
constitution/specification/planning/task structures guide these artifacts.

## User Scenarios & Testing

### US1 - Developer discovery and onboarding (P1)

A developer browses the complete Weather API, signs in with a seeded account,
and calls APIM through Try it. A second account can sign up independently.

Independent test: open a fresh browser session and get a live gateway response.
Acceptance: complete catalog, working CORS, signup submission, and an explicit
defer path for delayed verification email.

### US2 - Gateway security and policy development (P1)

A presenter proves key enforcement, validation, throttling, reusable fragments,
policy authoring, API tags, and baseline restoration.

Independent test: a fresh notebook kernel receives 401/400/200/429 on the
synthetic lab, then proves a visible response fragment.
Acceptance: no burst reaches the public upstream; lab edits do not affect MCP.

### US3 - Monitoring and investigation (P1)

A practitioner correlates current or explicitly labeled real preflight requests
through gateway metrics/logs and Application Insights.

Independent test: generate this module's own bounded traffic, inspect its
records, and show a real backend dependency without exposing secrets.

### US4 - REST-to-MCP and small assistant (P2)

A developer creates an additional native MCP endpoint in the portal, discovers
tools, calls one with the protocol client, and separately runs a real model
tool-calling notebook against the seeded server.

Independent test: skip live MCP creation and run the assistant against the seeded
server. It calls an allowed tool and grounds its answer in the actual result.

## Requirements

- FR-001: Preserve all operations from the complete upstream snapshot.
- FR-002: Use StandardV2 in Azure; local tools exclusively in the DevContainer.
- FR-003: Restore packages only through CFS and lock the tested dependency set.
- FR-004: Seed through `azd up` and provision/deploy lifecycle.
- FR-005: Include managed portal, pre-created account/subscription, and signup.
- FR-006: Include scoped keys, header validation, isolated throttling, fragments,
  policy creation, inheritance, and API tags.
- FR-007: Include real Monitor/Log Analytics and Application Insights evidence.
- FR-008: Seed native MCP with three selected read-only Weather tools.
- FR-009: Configure the existing Azure OpenAI model using AZD/Bicep parameters;
  authenticate through the presenter's CLI identity.
- FR-010: Allow at most three model turns, one tool per turn, validated arguments,
  bounded request time, and explicit model/tool failures.
- FR-011: Apply SecurityControl=Ignore to taggable created Azure resources.
- FR-012: Keep all modules independently runnable/skippable; no standup on stage.

## Edge cases

- Upstream outage: report it; never replace it with canned weather.
- Empty active alerts: valid, distinct from tool failure.
- Email delayed: defer verification and use the seeded account.
- Telemetry delayed: use labeled real preflight traffic; never manufacture logs.
- Model permission/tool-calling failure: fail that optional segment explicitly.
- CFS/TLS/auth failure: request approved connectivity/trust.
- Partial seed: create missing demo-owned account/subscription without rotating
  existing credentials; reject identity mismatch.

## Key entities

Complete API snapshot/inventory; scoped demo product/subscription; seeded user;
independent lab; reusable fragments; three MCP tools; correlated telemetry.

## Success Criteria

- SC-001: Fixed 55-minute modules plus a 5-minute discussion buffer.
- SC-002: Imported method/path inventory matches all 69 snapshot operations.
- SC-003: Protection produces 401/400/200 and a bounded lab 429.
- SC-004: Browser Try it and real MCP protocol calls succeed through APIM.
- SC-005: A real assistant uses an allowed tool and returns a grounded answer.
- SC-006: Every module runs without completing earlier modules.
- SC-007: Seed reruns preserve credentials; logs/notebooks contain no credentials.

## Assumptions

The presenter supplies a subscription, reachable region, approved container
runtime, public Weather.gov connectivity, a second email account, and an existing
tool-capable model with inference permission. No production security claim.
