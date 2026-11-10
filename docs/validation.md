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
| Python compilation and focused tests | Pass; 40 tests |
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
No actual live notebook section was executed against Azure.

The Azure validation workflow remains partial: authentication, explicit
subscription/region, provision preview, and Azure policy checks need the
presenter's deployment context. The deployment plan is not marked Validated.

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
| First managed portal publication/catalog | Published revision and consumer HTTP endpoint verified; browser catalog pending |
| Seeded sign-in and Try it/CORS | Pending |
| Independent signup/verification/approval | Pending |
| Lab 401/400/200/429 | Pass; missing/invalid key 401, missing intent 400, valid request 200, bounded burst 429 |
| Weather point and forecast through APIM | Pass; live point lookup and current forecast returned through the gateway |
| Credential stripping and source/MCP policy behavior | Pending |
| Actual gateway and Application Insights ingestion | Pending |
| Native MCP discovery/call/key denial | Pending |
| Existing model real allowed tool call/final answer | Pending |
| Seed repeatability and preserved credentials | Pass; reruns retained existing account/subscription credentials and the complete hook succeeded |
| Independent skip/reset/repeat for every module | Pending |
| Full presentation within 60 minutes | Pending |

The read-only operation inventory check also confirmed the backing IDs `point`,
`gridpoint_forecast`, and `alerts_active_area` exist in APIM. It did not redeploy
the corrected MCP tools or prove MCP discovery/calls; those gates remain pending.

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
was verified absent from AZD configuration. Browser sign-in/Try it, telemetry,
MCP calls, and model inference remain separate pending acceptance gates.
