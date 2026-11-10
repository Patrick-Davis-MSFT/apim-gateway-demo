# Prepare before the presentation

## 1. Open the DevContainer

Host prerequisites: VS Code with Dev Containers support and an approved
Linux-container runtime. **Do not install Python, Azure CLI, AZD, Bicep, Spec Kit,
or notebook packages on the host.**

1. Open this folder in VS Code.
2. Run **Dev Containers: Reopen in Container**.
3. Allow the local image to build. The base image comes from Microsoft Container
   Registry; AZD/Bicep binaries come from their official vendor releases.
4. Select **Python 3 (DevContainer)** for the walkthrough notebook.
5. In the **container terminal**, run:

   ```sh
   python scripts/preflight.py --local
   python scripts/validate.py
   ```

The container uses the CFS Python index and a hash-locked
[dependency set](../requirements.lock). No public package fallback is configured.
The [Dockerfile](../.devcontainer/Dockerfile) also carries the requested npm,
Yarn, NuGet, and uv settings. No remote build or deployed runtime needs CFS.

### CFS trust and package failures

Corporate network reachability does not necessarily mean Linux container trust.
If the build/preflight reports TLS, proxy, or authentication errors, obtain the
approved corporate CA, proxy settings, or separate login configuration before
rebuilding. Do not use `--trusted-host`, `--insecure`, `verify=False`, or a public
index. Do not embed credentials/certificates in source or build layers.

`NUGET_PACKAGES` deliberately preserves the requested feed URL, but NuGet normally
treats that variable as a cache directory. This Python demo does not restore .NET
packages. If adding a NuGet operation, use the configured CFS source and override
its cache path for that invocation, for example:

```sh
NUGET_PACKAGES=/tmp/nuget-cache dotnet restore --configfile .devcontainer/NuGet.Config
```

If PowerShell is later needed, register the appropriate corporate repository:

- PSResourceGet: `https://packagefeedproxy.microsoft.io/powershell/v3/index.json`
- PowerShellGet 2.x: `https://packagefeedproxy.microsoft.io/powershell/v2`

PowerShell/.NET/npm/Yarn are not dependencies of this walkthrough.
[CFS documentation](https://aka.ms/CFS) requires user login.
The engineering-documentation MCP at `https://mcp.eng.ms` requires a separate
user login; GitHub Copilot authentication does not grant it.

## 2. Sign in and select the disposable Azure environment

All commands below run in the **container terminal**, before the presentation.
Use a new AZD environment for each disposable resource group.

If you started with `azd provision` and it already created an environment, reuse
that environment: skip `azd env new` below (or select it with
`azd env select <environment-name>`). The preprovision hook now prompts for
missing configuration in an interactive terminal and saves each answer in the
selected AZD environment. It does not choose a subscription or region for you;
the subscription must match your explicitly selected Azure CLI account.
You can also configure all values explicitly as follows.

Replace every angle-bracket placeholder below with a real value; do not save
the placeholder text literally.

```sh
az login --use-device-code
azd auth login --use-device-code
az account set --subscription "<subscription-id>"
azd env new apimweather
azd env set AZURE_SUBSCRIPTION_ID "<subscription-id>"
azd env set AZURE_LOCATION eastus
azd env set PUBLISHER_EMAIL "<presenter-controlled-email>"
azd env set WEATHER_CONTACT "<real-contact-email-or-application-contact-URL>"
azd env set DEMO_DEVELOPER_EMAIL "<seeded-developer-email>"
azd env set AZURE_OPENAI_ENDPOINT "https://<existing-resource>.openai.azure.com"
azd env set AZURE_OPENAI_DEPLOYMENT "<existing-tool-capable-deployment>"
python scripts/preflight.py --configuration
```

For guided configuration without provisioning, run
`python scripts/preflight.py --configuration --interactive`.
The command without `--interactive` remains a read-only configuration check.
Existing non-placeholder values are retained. Empty/placeholder answers are
rejected; successfully saved answers are retained if setup is interrupted.
For unattended runs, set `AZD_NON_INTERACTIVE=true` and configure all values
before provisioning; missing values fail with the required `azd env set` commands
instead of prompting. Non-interactive terminals also never prompt.

Check Azure-side readiness before provisioning:

```sh
azd auth login --check-status
azd provision --preview --no-prompt
```

Review the preview and resolve subscription/region, quota, role-assignment, and
Azure Policy failures before `azd up`. Local Bicep compilation and configuration
preflight are not proof that those Azure-side checks pass.

The model endpoint must be the resource root, without `/openai` or a deployment
path. It is an input to Bicep and a non-secret AZD output; no model is created.
The notebook uses Azure OpenAI's v1 chat API and requires a deployment supporting
function calling and `max_completion_tokens`. Validate it before presenting.

Required permissions:

- Create resources/deployments in the selected subscription and assign APIM's
  narrowly scoped Application Insights telemetry role. Contributor alone may
  not permit role assignments; use an approved role/administrator.
- Read APIM configuration/subscription secrets and query telemetry.
- Existing model inference access, such as **Cognitive Services OpenAI User** on
  the model resource, for the identity used by `az login`.

Confirm Standard v2 availability in the chosen region and subscription. East US
is a preference, not a fallback deployment. Resolve quota/Azure policy failures
explicitly. `SecurityControl=Ignore` is metadata, not a policy bypass.

## 3. Provision and seed

```sh
azd up
```

Equivalent separated workflow:

```sh
azd provision
azd deploy
```

Do not run both workflows unnecessarily. The deployment creates one-unit
**StandardV2**, a workspace, Application Insights, and the APIM configuration.
The `postprovision` hook then:

1. Creates missing seeded developer/subscription resources from Bicep.
2. Privately prompts for the initial developer password only when that user is
   absent. Choose at least 12 characters and retain it securely for portal login.
   Password input is hidden, including when you type or paste.
3. Retains existing credentials on rerun.
4. Verifies the full imported method/path inventory.
5. Restores the synthetic lab baseline.
6. Publishes the default managed portal and checks its endpoint.
7. Sends bounded real/synthetic traffic and records its non-secret run ID.

This is an infrastructure-only AZD project: `azd provision` runs the seed hook;
`azd deploy` has no application services to deploy. It is safe to follow the
requested two-command workflow, but do not rely on a no-services deploy hook.
Rerun operational seeding explicitly with `azd hooks run postprovision`.

The seeded developer email must not already belong to another APIM user,
including the service administrator. If it does, set `DEMO_DEVELOPER_EMAIL` to a
different presenter-controlled email; the seed never reuses or overwrites that
other account. For a failed `seed-developer` deployment, credential-bearing
output stays redacted. Check the deployment status and inspect errors privately
in **Azure Portal > Resource group > Deployments > seed-developer**. If the
deployment is still `Running`, wait for it to finish before retrying the hook.
Do not share deployment parameter files, raw debug logs, or passwords.

Seeding does not write weather records upstream. "Seed data" means demo catalog,
configuration, user/subscription, and actual preflight telemetry.

Do not print `azd env get-values`, subscription `listSecrets`, or access-token
commands on screen. AZD's ignored local environment contains configuration,
including account/contact identifiers. Do not commit/share it.

## 4. Prove live readiness

```sh
python scripts/preflight.py --live --wait-telemetry --ai
```

This checks the full import, live point/forecast, lab protection, native MCP, real
log ingestion, and the existing model's actual tool call. It does not configure
permissions or create a model. A new workspace can take substantial time to
ingest its first records; finish this **before** the event. The bounded wait
fails explicitly if records have not arrived; rerun later, not on stage.

Then verify the browser-only acceptance checklist:

- Open the published URL from **APIM > Developer portal > Portal overview** in a
  normal consumer/private session, not only the administrative visual editor.
- Confirm the Weather product and complete API reference are present.
- Sign in as the seeded developer with the password supplied privately.
- Open **APIs > National Weather Service - complete API**, select the point
  operation, and use **Try it** with `38.8894`, `-77.0352`.
- Select the seeded product subscription. Confirm a 200 response and no CORS
  error. Never project the key field; mask/collapse it.
- Test the signup/verification workflow with a separate presenter-controlled
  email account. Use another address for the live signup if the test account
  already exists. Keep email notifications off the projected screen.
- Check **Monitoring > Analytics/Metrics**, gateway logs, and Application
  Insights for actual preflight evidence.
- Open the notebook, restart its kernel, and run each selected module starting
  at its own setup cell. Rehearse skipping prior modules and repeating/resetting.
- Rerun `azd hooks run postprovision` to prove operational seed repeatability. Do not change
  publisher/developer identities mid-demo.

Opening a portal HTML page is not proof of sign-in, API catalog, or Try it.
Do not present until these live checks pass. Record actual results in
[validation.md](validation.md).

## Spec Kit development workflow

Spec Kit is already initialized with bundled assets from the CFS-installed CLI.
Do not reinitialize over customized files just to run the demo.

In Copilot Chat inside the container, review the
[constitution](../.specify/memory/constitution.md), [feature](../specs/001-apim-walkthrough/spec.md),
[plan](../specs/001-apim-walkthrough/plan.md), and
[tasks](../specs/001-apim-walkthrough/tasks.md).

For a new change use `/speckit-specify`, `/speckit-clarify`, `/speckit-plan`,
`/speckit-tasks`, and `/speckit-analyze`, reviewing each result before
`/speckit-implement`. These are Copilot skills, not shell commands. Command
spelling comes from the installed version, not an older tutorial.

For intentional dependency updates, resolve only through CFS, regenerate the
lock in the container, rebuild, and rerun validation:

```sh
uv pip compile --generate-hashes requirements.in -o requirements.lock
```

Refresh the full upstream snapshot only deliberately:

```sh
python scripts/prepare_api.py
python scripts/build_notebook.py
python scripts/validate.py
```

Updating the API requires checking the operation inventory and MCP references,
not silently accepting a smaller import.

The refresh preserves the upstream snapshot and generates the APIM-compatible
OpenAPI 3.0.3 import, recording hashes and compatibility changes in the inventory.
To regenerate that import from the existing snapshot without contacting
Weather.gov, run:

```sh
python scripts/prepare_api.py --from-snapshot
```
