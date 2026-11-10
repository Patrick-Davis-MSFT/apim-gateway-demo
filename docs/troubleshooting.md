# Troubleshooting, resets, and cleanup

Failures are surfaced rather than converted to a successful-looking demo.
Run setup commands only in the DevContainer.

| Symptom | Action |
| --- | --- |
| CFS/TLS/proxy/login failure | Obtain approved CA, proxy, or separate login. Rebuild; never disable TLS or switch registries. |
| Tool missing in container | Rebuild from the checked-in Dockerfile. Do not install on the host. |
| Missing `AZURE_SUBSCRIPTION_ID` or other configuration on first provision | Reuse the environment already created. Follow setup section 2, or rerun `azd provision` in an interactive terminal to supply missing values. Use `python scripts/preflight.py --configuration --interactive` to configure without provisioning. No subscription/region is chosen automatically. |
| Wrong Azure subscription | Compare AZD configuration and `az account show`; explicitly select the intended subscription. |
| Region/SKU/policy failure | Verify Standard v2 availability/quota/policy before provisioning. Do not silently choose another tier/region. |
| Telemetry role assignment denied | Use an approved identity able to grant the scoped role; do not broaden access to work around it. |
| Seed asks for password | The demo developer is absent. Supply a private initial password; it is not saved in AZD. |
| Seeded email differs | Resolve the identity/configuration explicitly. The seed intentionally refuses to overwrite an existing user. |
| Seed email already belongs to another APIM user | Set `DEMO_DEVELOPER_EMAIL` to a different presenter-controlled email with `azd env set`. This includes collisions with the existing administrator; the seed will not reuse or overwrite that account. Retry only the postprovision hook. |
| Seed deployment fails with credential output redacted | Check `seed-developer` under the resource group's Deployments in Azure Portal. If still `Running`, wait for completion before retrying. Resolve the reported error privately, then run `azd hooks run postprovision`; never share raw debug logs/parameters or disable credential redaction. |
| JSON parsing reports `Unexpected UTF-8 BOM` or `Expecting value` during lab reset | APIM policy updates can return XML unless `Accept=application/json` is explicit; CLI `--output json` alone does not negotiate the server response. The updated management helper requests JSON, and the CLI helper removes a leading byte-order mark. Rerun `azd hooks run postprovision`; existing credentials are retained. |
| Full API import mismatch | Inspect `api/inventory.json` and imported method/path pairs. Do not accept a smaller API or only validate the three tools. |
| OpenAPI import reports “Cannot create a scalar value” at a schema `type` | APIM rejects OpenAPI 3.1 nullable type arrays. Bicep must import the generated `api/weather.apim.openapi.json` (3.0.3), not the raw snapshot. Regenerate with `python scripts/prepare_api.py --from-snapshot`, validate, and rerun `azd provision` in the same environment; do not delete the resources already created. |
| Portal publication fails | Inspect Portal overview and portal revision state. Confirm Standard v2 portal enabled and supported default initialization. Do not claim a hidden manual first visit is automated. |
| Consumer catalog absent | Confirm product is published, APIs are bound, groups are visible, and the current portal revision completed. |
| Try it CORS error | Confirm global/API CORS uses the actual published origin and runs before access to backend. Browser OPTIONS has no key; product-only CORS is insufficient. |
| Signup email delayed | Explicitly defer verification and continue with the seeded account. Check the email flow outside the presentation. |
| Probe remains 429 | Its counter expires in ten seconds. Repeat via M2; do not increase the limit just to force success. |
| No probe 429 | Inspect lab policy/fragment inclusion. The helper stops after 12 attempts and never targets Weather.gov. |
| No new log rows | Distinguish ingestion lag from permissions/query errors. Use the labeled real preflight run. Complete first-ingestion readiness before the event. |
| MCP initialization/tool failure | Check URL `/weather-mcp/mcp`, product key, source operation bindings/parameter schemas, policy scopes, and streaming-safe diagnostics. |
| MCP deployment says a backing operation ID was not found | Use the exact imported IDs: `point`, `gridpoint_forecast`, and `alerts_active_area`. APIM retains underscores and case; hyphenated guesses are different IDs. Rerun `azd provision` in the same environment after correcting the bindings. |
| MCP tool unexpectedly bypasses source policies | Stop live acceptance. Verify documented source-operation behavior and fix the explicit MCP/source boundary before presenting. |
| Existing model 401/403 | Check the CLI identity and inference role on that existing resource; AZD login and CLI login are separate. |
| Model rejects tool/API parameters | Use a compatible existing deployment and v1 endpoint; validate tool calling before the event. |
| Model/tool/context limit reached | Report the bounded failure. Use the point-only prompt; do not silently fabricate or truncate a weather answer. |
| Weather.gov outage/5xx | Report the upstream outage. Do not replace current data with recordings. Use the synthetic lab for policy-only learning. |

## Reset only what the module owns

In the visible notebook M2/M3 reset cell:

```python
demo.reset_lab()
```

This restores only `lab-protection`, `lab-response`, and the `security-lab` policy
from their checked-in XML. It does not rotate keys, delete users, edit Weather,
or replace the seeded MCP server.

The extra `presenter-response` fragment can remain unreferenced. The extra
`presenter-mcp` server can remain until resource-group cleanup. Do not delete
unknown fragments/servers or broadly reset an APIM instance.

Rerun the operational seed outside the presentation:

```sh
azd hooks run postprovision
```

For declarative baseline changes, run `azd provision` then `azd deploy`.
Neither action is part of the timed presentation.

## Cleanup

**Destructive, explicit human action after the event.**
Confirm the selected AZD environment and the exact disposable resource group
in the Azure portal. The resource group contains paid Standard v2 and telemetry
resources even when the demo is idle.

From the DevContainer:

```sh
azd down
```

Read and confirm its prompts. Do not add automatic cleanup hooks, blanket
subscription deletion, or `--force` to a live demonstration. The existing model
resource is not part of this deployment and must remain.

Clear notebook outputs before saving/sharing. Remove local credentials using
`az logout` / `azd auth logout` when no longer needed. Rebuilding/removing the
DevContainer does not delete Azure resources.
