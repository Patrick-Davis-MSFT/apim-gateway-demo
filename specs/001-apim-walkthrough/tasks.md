# Tasks: APIM walkthrough

Input: [spec.md](spec.md), [plan.md](plan.md), and module contracts.
Execution status is in the session todo database and validation report; task
contracts do not claim live acceptance.

## Setup and foundation

- T001 Configure .devcontainer/Dockerfile and requirements.lock with CFS-only tools.
- T002 Initialize Spec Kit and review .specify/memory/constitution.md.
- T003 Snapshot/validate the full contract using scripts/prepare_api.py.
- T004 Define infra/main.bicep and AZD lifecycle in azure.yaml.

## US1 - Developer onboarding

- T005 [US1] Define product/catalog and portal in infra/demo.bicep.
- T006 [US1] Preserve account/subscription credentials with infra/developer.bicep
  and scripts/seed.py; publish using infra/portal.bicep.
- T007 [US1] Document fresh browser, Try it, signup, and defer in docs/modules.md.
- T008 [US1] Live acceptance: publication, sign-in, CORS, and signup.

## US2 - Security and developer workflow

- T009 [US2] Implement policies/fragments and isolated synthetic probe.
- T010 [US2] Build protection and lab reset in scripts/demo.py.
- T011 [US2] Add tag/fragment walkthrough and independent notebook sections.
- T012 [US2] Test failure codes, credential stripping, and reset ownership.

## US3 - Monitoring

- T013 [US3] Define telemetry resources, safe diagnostics, and MI logger.
- T014 [US3] Add independent traffic, KQL, and preflight-run labeling.
- T015 [US3] Live acceptance: actual ingestion and dependency correlation.

## US4 - MCP and AI

- T016 [US4] Define native MCP/tools in infra/demo.bicep.
- T017 [US4] Implement real protocol calls and bounded model loop in scripts/demo.py.
- T018 [US4] Test allowlists, schemas, errors, and loop/context bounds.
- T019 [US4] Live acceptance: key denial, tools, model, grounded answer.

## Cross-cutting acceptance

- T020 Validate Bicep, full inventory, XML, notebooks, CFS, docs, secret handling.
- T021 Verify repeat seeding, independent entry/reset, and 60-minute ceiling.

Dependencies: T001 -> T002 -> T003 -> T004. User stories follow the baseline;
presentation modules have no dependencies on earlier demonstrations.
Documentation/KQL and helper tests can proceed independently after contracts.
