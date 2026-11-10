# Validation record

## Local/container checks

Implementation checks were run using the local DevContainer image, not host
tool installations:

| Check | Result |
| --- | --- |
| CFS connectivity and package restoration | Pass; no public fallback |
| Complete OpenAPI validation/hash/inventory | Pass; preserved 3.1.2 snapshot and validated 3.0.3 APIM import; all 69 operations retained |
| APIM compatibility conversion | Pass; 27 nullable type arrays, 4 null-only branches, 13 schema example arrays, and version change recorded; reversible conversion verified |
| Bicep main/developer/portal compilation | Pass; no compiler warnings |
| Policy XML and inheritance checks | Pass |
| Python compilation and full test suite | Pass; 52 tests on 2026-11-10 |
| MCP backing operation ID contract | Pass; all three Bicep bindings match the import's exact IDs, including underscores |
| Seed email conflict and credential-safe failure handling | Pass; 5 targeted seed tests, Python compilation, and syntax check; failure cleanup removes temporary parameter file |
| CLI response parsing and management content negotiation | Pass; 20 shared-helper/seed tests and syntax check; BOM normalization and explicit JSON Accept header covered |
| Six independent notebook setup kernels | Pass with mocked Azure access |
| Notebook schema/reproducibility/empty saved outputs | Pass |
| Relative documentation links | Pass |
| AZD infrastructure-only project parsing | Pass |
| Official Azure YAML JSON schema | Pass against the direct Azure repository schema |
| Spec Kit feature/task artifact discovery | Pass |

Toolchain exercised: Python 3.12.16, Azure CLI 2.92.0, AZD 1.37.3, Bicep 0.49.2,
Spec Kit 1.3.2, and uv 0.13.6. Package versions are recorded in the lock file.
All 21 notebook code cells were subsequently executed against the existing
Azure environment on 2026-11-10; see the live notebook execution record below.

The deployment validation workflow remains partial: a successful notebook run
against existing resources does not prove a new provision preview or Azure
Policy acceptance. The deployment plan is not marked Validated.

Reproduce with:

```sh
python scripts/preflight.py --local
python scripts/validate.py
```

## Live acceptance: partial verification

No Azure provisioning, signup, model inference, or live APIM test is implied by
a successful local build. The presenter must run the live acceptance in
[setup.md](setup.md) and record actual results here:

| Gate | Actual result |
| --- | --- |
| `azd up` or provision/deploy hooks | Postprovision hook succeeded against the existing infrastructure |
| All snapshot operations imported | Pass; read-only Azure management query verified all 69 method/path/operation-ID bindings against the corrected inventory |
| First managed portal publication/catalog | Pass; published endpoint and browser catalog verified |
| Seeded sign-in and Try it/CORS | Pass; signed-in browser point request returned 200 after allowing the console's Cache-Control and X-Ms-Client-Request-Id headers |
| Independent signup/verification/approval | Pending |
| Lab 401/400/200/429 | Pass; missing/invalid key 401, missing intent 400, valid request 200, bounded burst 429 |
| Weather point and forecast through APIM | Pass; live point lookup and current forecast returned through the gateway |
| Credential stripping and source/MCP policy behavior | Pending |
| Actual gateway and Application Insights ingestion | Pass; historical preflight gateway query returned 13 records, notebook Application Insights query returned 20 records, and a separate backend query found 36 successful Weather.gov dependencies |
| Native MCP discovery/call/key denial | Pass; missing key returned 401, all three seeded tools were discovered, and real point calls succeeded |
| Existing model real allowed tool call/final answer | Pass; Washington, DC city-name prompt produced numeric point-tool arguments, a real MCP result, and a nonempty grounded answer |
| Seed repeatability and preserved credentials | Pass; reruns retained existing account/subscription credentials and the complete hook succeeded |
| Independent skip/reset/repeat for every module | Partial; all modules passed sequentially with their own setup cells, M3 reset was verified live, and six independent setup kernels passed locally; full live skip/repeat matrix not exercised |
| Full presentation within 60 minutes | Pending |

The read-only operation inventory check also confirmed the backing IDs `point`,
`gridpoint_forecast`, and `alerts_active_area` exist in APIM. The later live
notebook execution additionally proved MCP discovery and point-tool calls.

## Live notebook execution: 2026-11-10

Executed every code cell in the saved
[walkthrough notebook](../notebooks/walkthrough.ipynb) in a fresh Jupyter kernel
against the existing APIM, Log Analytics workspace, and configured model.
Execution ran from 15:34:07 to 15:35:30 UTC, including prerequisite preparation
and final lab cleanup. No cell was skipped or mocked; no runtime fixes were
needed during this verification.

| Module | Code cells | Actual result |
| --- | --- | --- |
| M1 | 3/3 pass | Independent setup, all 69 API operation bindings, live point and forecast through APIM |
| M2 | 3/3 pass | Lab reset; missing/invalid keys 401, missing intent 400, valid synthetic request 200, bounded burst 429 |
| M3 | 4/4 pass | Independent setup, API tags, presenter-fragment response/header, and baseline reset |
| M4 | 5/5 pass | Real traffic, current-run ingestion-lag notice, historical preflight records, and Application Insights query |
| M5 | 4/4 pass | Missing-key 401, three-tool discovery, direct point call, and existing weather-mcp verification cell |
| M6 | 2/2 pass | Exact prompts displayed; model selected weather_point with latitude 38.9072 and longitude -77.0369 from the city-name request and returned a grounded answer |

M3's documented external prerequisite was performed through Azure management:
created/updated the demo-owned `presenter-response` fragment, changed only the
lab policy's response-fragment reference, and verified the live header before
executing the proof cell. The notebook's reset and an additional final reset
restored the synthetic lab baseline, verified with a real request. The
unreferenced presenter fragment remains available for the demonstration.

The immediate M4 current-run query returned no records and displayed its
documented ingestion-lag message. Its historical preflight query returned 13
real records, and its Application Insights query returned 20 records. A
follow-up query confirmed 36 successful Weather.gov dependency records; it did
not yet find the new M4 run ID. Fresh ingestion is asynchronous, not a cell
failure or fabricated result.

The saved notebook retains empty outputs and execution counts; live execution
results and credentials were not written into it. The complete local validator
also passed Python compilation, both OpenAPI contracts, policy XML, all three
Bicep entry points, notebook reproducibility, documentation links, and 52 tests.
This run does not cover independent signup/email verification, manual portal
authoring UX, a fresh infrastructure deployment, or presentation timing.

A subsequent read-only seed investigation found that `DEMO_DEVELOPER_EMAIL`
already belongs to another APIM user while `demo-developer` is absent. The
`seed-developer` deployment remained `Running`, with its user operation reporting
`BadGateway` / `InternalServerError`; these observations do not establish that the
email collision caused the provider error. Configure an unused developer email
and resolve the active deployment before retrying the postprovision hook.

Resolution: with approval, the stalled deployment was canceled and an unused
presenter-controlled email alias was configured. The developer seed subsequently
reached `Succeeded`. The complete postprovision hook then passed after fixing
APIM policy response negotiation (`Accept=application/json`) and CLI BOM
normalization. The initial password was supplied only to the seed process and
was verified absent from AZD configuration. Subsequent browser and notebook
verification completed the sign-in/Try it, historical telemetry, MCP, and model
inference gates recorded above; independent signup remains pending.
