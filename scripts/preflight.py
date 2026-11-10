"""Fail explicitly on local/configuration/live readiness problems."""

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from urllib.parse import urlsplit

import httpx2 as httpx

from demo import Demo, assistant, cli, environment, require_container

FEEDS = {
    "PIP_INDEX_URL": "https://packagefeedproxy.microsoft.io/pypi/simple",
    "NPM_CONFIG_REGISTRY": "https://packagefeedproxy.microsoft.io/npm/",
    "YARN_NPM_REGISTRY_SERVER": "https://packagefeedproxy.microsoft.io/npm/",
    "NUGET_PACKAGES": "https://packagefeedproxy.microsoft.io/nuget/v3/index.json",
    "UV_DEFAULT_INDEX": "https://packagefeedproxy.microsoft.io/pypi/simple",
}
CONFIGURATION_PROMPTS = {
    "AZURE_SUBSCRIPTION_ID": "Azure subscription ID (must match az account show)",
    "AZURE_LOCATION": "Azure region supporting Standard v2 (for example eastus)",
    "PUBLISHER_EMAIL": "Presenter-controlled publisher email",
    "WEATHER_CONTACT": "Weather.gov contact email or application contact URL",
    "DEMO_DEVELOPER_EMAIL": "Seeded demo developer email",
    "AZURE_OPENAI_ENDPOINT": "Existing Azure OpenAI HTTPS resource root (without /openai)",
    "AZURE_OPENAI_DEPLOYMENT": "Existing tool-capable Azure OpenAI deployment name",
}


def local() -> None:
    require_container()
    for name, value in FEEDS.items():
        if os.environ.get(name) != value:
            raise RuntimeError(f"{name} must point to the documented CFS endpoint.")
    for name in ("PIP_EXTRA_INDEX_URL", "UV_EXTRA_INDEX_URL", "UV_INDEX"):
        if os.environ.get(name):
            raise RuntimeError(f"Unset {name}; this demo does not allow additional package indexes.")
    for tool in ("az", "azd", "specify", "python"):
        if not shutil.which(tool):
            raise RuntimeError(f"Missing container tool: {tool}. Rebuild the DevContainer.")
    response = httpx.get(FEEDS["PIP_INDEX_URL"] + "/specify-cli/", timeout=30, follow_redirects=False)
    response.raise_for_status()
    if "specify_cli-" not in response.text:
        raise RuntimeError("CFS did not return Python distributions. Check separate corporate authentication.")
    print("Container tools and CFS connectivity/trust: PASS (no public fallback).")


def configuration(*, interactive: bool = False) -> None:
    local()
    values = environment()
    if not values.get("AZURE_ENV_NAME"):
        raise RuntimeError("Create or select an AZD environment using azd env new or azd env select.")
    missing = [
        name for name in CONFIGURATION_PROMPTS
        if not values.get(name, "").strip() or "<" in values[name]
    ]
    commands = "\n".join(f'  azd env set {name} "<value>"' for name in missing)
    if missing:
        if (
            not interactive or not sys.stdin.isatty()
            or os.environ.get("AZD_NON_INTERACTIVE", "").lower() in ("true", "1")
        ):
            raise RuntimeError(
                "Missing required Azure configuration. Run these commands with real values:\n"
                f"{commands}\nSee docs/setup.md, section 2."
            )
        print("Complete the selected AZD environment before provisioning. Values are saved with azd env set.")
        for name in missing:
            try:
                value = input(f"{CONFIGURATION_PROMPTS[name]} ({name}): ").strip()
            except EOFError as exc:
                raise RuntimeError(
                    f'Input unavailable. Configure {name} using azd env set {name} "<value>".'
                ) from exc
            if not value or "<" in value:
                raise RuntimeError(
                    f'Enter a real value for {name} using azd env set {name} "<value>", then retry.'
                )
            cli("azd", "env", "set", name, value)
            values[name] = value
    endpoint = urlsplit(values["AZURE_OPENAI_ENDPOINT"])
    if (
        endpoint.scheme != "https" or not endpoint.hostname
        or not endpoint.hostname.endswith((".openai.azure.com", ".cognitiveservices.azure.com"))
        or endpoint.path not in ("", "/") or endpoint.username or endpoint.password
        or endpoint.query or endpoint.fragment
    ):
        raise ValueError("AZURE_OPENAI_ENDPOINT must be the HTTPS resource root, without /openai.")
    account = json.loads(cli("az", "account", "show", "--output", "json"))
    if account["id"] != values["AZURE_SUBSCRIPTION_ID"]:
        raise RuntimeError("Azure CLI subscription differs from AZD. Run az account set explicitly.")
    cli("azd", "version")
    cli("az", "bicep", "version")
    print("Azure context and required configuration: PASS. No resources created.")


def telemetry(demo: Demo, wait_seconds: int) -> None:
    apim_id = demo.config["APIM_RESOURCE_ID"].lower()
    gateway = (
        "union isfuzzy=true ApiManagementGatewayLogs, (datatable(_ResourceId:string)[])"
        f" | where tolower(_ResourceId) == '{apim_id}' | take 1"
    )
    app_id = (
        f"/subscriptions/{demo.config['AZURE_SUBSCRIPTION_ID']}/resourcegroups/"
        f"{demo.config['AZURE_RESOURCE_GROUP']}/providers/microsoft.insights/components/"
        f"{demo.config['APPLICATION_INSIGHTS_NAME']}"
    ).lower()
    app = (
        "union isfuzzy=true AppRequests, (datatable(_ResourceId:string)[])"
        f" | where tolower(_ResourceId) == '{app_id}' | take 1"
    )
    dependencies = (
        "union isfuzzy=true AppDependencies, (datatable(_ResourceId:string,Target:string)[])"
        f" | where tolower(_ResourceId) == '{app_id}' and Target contains 'api.weather.gov' | take 1"
    )
    deadline = time.monotonic() + wait_seconds
    while True:
        # Query errors are not "no records": fail rather than hide permissions/schema failures.
        gateway_rows = demo.query(gateway)["tables"][0]["rows"]
        app_rows = demo.query(app)["tables"][0]["rows"]
        dependency_rows = demo.query(dependencies)["tables"][0]["rows"]
        if gateway_rows and app_rows and dependency_rows:
            print("Gateway and Application Insights request/dependency ingestion: PASS.")
            return
        if time.monotonic() >= deadline:
            raise RuntimeError("Telemetry has not arrived yet. Rerun --live --wait-telemetry before presenting.")
        print("Waiting for real telemetry ingestion; no synthetic log records are inserted.")
        time.sleep(30)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--configuration", action="store_true")
    parser.add_argument("--interactive", action="store_true",
                        help="Prompt for missing configuration and save it in the selected AZD environment.")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--wait-telemetry", action="store_true")
    parser.add_argument("--ai", action="store_true")
    args = parser.parse_args()
    if args.configuration:
        configuration(interactive=args.interactive)
    elif args.live:
        demo = Demo.load()
        print(demo.verify_inventory())
        print(demo.weather())
        print(demo.protection())
        print(asyncio.run(demo.mcp_tools()))
        print(asyncio.run(demo.mcp_call("weather_alerts", {"area": "VA"})))
        denial = demo.request("/weather-mcp/mcp", method="POST", key_mode="missing")
        demo.expect(denial, 401, "MCP without subscription key")
        telemetry(demo, 1200 if args.wait_telemetry else 0)
        if args.ai:
                print(asyncio.run(asyncio.wait_for(assistant(demo), timeout=120)))
        print("Complete the browser-only portal/signup acceptance checklist in docs/setup.md.")
    else:
        local()


if __name__ == "__main__":
    main()
