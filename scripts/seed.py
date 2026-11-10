"""Operational AZD seed steps. Azure resources remain defined in Bicep."""

import getpass
import json
import os
import shlex
import tempfile
import time

import httpx2 as httpx

from demo import Demo, ROOT, cli, environment, require_container


def deploy_template(config: dict, template: str, values: dict, *, sensitive: bool = False) -> None:
    parameters = {name: {"value": value} for name, value in values.items()}
    # NamedTemporaryFile is created with owner-only permissions; always remove it.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as file:
        json.dump({"parameters": parameters}, file)
        file.flush()
        try:
            cli(
                "az", "deployment", "group", "create",
                "--name", f"seed-{template}",
                "--resource-group", config["AZURE_RESOURCE_GROUP"],
                "--template-file", str(ROOT / "infra" / f"{template}.bicep"),
                "--parameters", f"@{file.name}", "--output", "none", sensitive=sensitive,
            )
        except RuntimeError:
            if not sensitive:
                raise
            command = (
                "az deployment group show "
                f"--resource-group {shlex.quote(config['AZURE_RESOURCE_GROUP'])} "
                f"--name {shlex.quote(f'seed-{template}')} "
                "--query properties.provisioningState --output tsv"
            )
            raise RuntimeError(
                f"Seed deployment 'seed-{template}' failed; credential-bearing output is redacted.\n"
                f"Check its status without exposing credentials:\n  {command}\n"
                "If it is Running, wait for a terminal state before retrying. "
                "Inspect the deployment's error privately in Azure Portal > Resource group > Deployments. "
                "After resolving the error, rerun azd hooks run postprovision."
            ) from None


def seed_account(config: dict) -> None:
    # No key is required for management-plane calls.
    management = Demo(config, "")
    users = management.list_arm("users")
    subscriptions = management.list_arm("subscriptions")
    existing = next((u for u in users if u["name"] == "demo-developer"), None)
    if existing and existing["properties"]["email"].casefold() != config["DEMO_DEVELOPER_EMAIL"].casefold():
        raise RuntimeError("Seeded user's email differs from configuration. Resolve explicitly; no account was overwritten.")
    if not existing and any(
        u["properties"]["email"].casefold() == config["DEMO_DEVELOPER_EMAIL"].casefold()
        for u in users
    ):
        raise RuntimeError(
            "DEMO_DEVELOPER_EMAIL already belongs to another APIM user. "
            "The seed will not overwrite or reuse that account. "
            'Choose a different email with azd env set DEMO_DEVELOPER_EMAIL "<unused-email>", '
            "then rerun azd hooks run postprovision."
        )
    existing_subscription = next((s for s in subscriptions if s["name"] == "demo-presenter"), None)
    has_subscription = existing_subscription is not None
    if existing_subscription:
        properties = existing_subscription["properties"]
        if (
            properties.get("scope", "").lower() not in {
                "/products/weather-demo", (config["APIM_RESOURCE_ID"] + "/products/weather-demo").lower(),
            }
            or properties.get("ownerId", "").lower() not in {
                "/users/demo-developer", (config["APIM_RESOURCE_ID"] + "/users/demo-developer").lower(),
            }
            or properties.get("state") != "active"
        ):
            raise RuntimeError("Existing presenter subscription has unexpected scope/owner/state; resolve explicitly.")
    if existing and has_subscription:
        print("Existing demo account/subscription retained; credentials unchanged.")
        return
    password = ""
    if not existing:
        password = os.environ.get("DEMO_INITIAL_PASSWORD") or getpass.getpass(
            "Choose a password for the seeded developer (at least 12 characters; input hidden; not saved in AZD): "
        )
        if len(password) < 12:
            raise ValueError("Use a demo password of at least 12 characters.")
    deploy_template(config, "developer", {
        "apimName": config["APIM_NAME"], "email": config["DEMO_DEVELOPER_EMAIL"],
        "password": password, "createUser": existing is None,
        "createSubscription": not has_subscription,
    }, sensitive=True)
    print("Missing demo account/subscription created. No keys or password were printed.")


def publish_portal(demo: Demo) -> None:
    revisions = demo.list_arm("portalRevisions")
    published = next((
        r for r in revisions
        if r["properties"].get("isCurrent")
        and r["properties"].get("status") == "completed"
    ), None)
    if not published:
        deploy_template(demo.config, "portal", {"apimName": demo.config["APIM_NAME"]})
    deadline = time.monotonic() + 600
    while True:
        revisions = demo.list_arm("portalRevisions")
        if any(r["properties"].get("isCurrent") and r["properties"].get("status") == "completed" for r in revisions):
            response = httpx.get(demo.config["DEVELOPER_PORTAL_URL"], timeout=30, follow_redirects=True)
            if response.status_code == 200:
                print("Managed portal revision published and consumer endpoint responds.")
                return
            if response.status_code not in (404, 502, 503):
                raise RuntimeError(f"Published developer portal returned HTTP {response.status_code}.")
        elif any(r["name"] == "seed-v1" and r["properties"].get("status") == "failed" for r in revisions):
            raise RuntimeError("Portal publication failed. Inspect Developer portal > Portal overview; do not present yet.")
        if time.monotonic() >= deadline:
            raise RuntimeError("Portal was not ready within its readiness budget. No manual first visit is assumed.")
        time.sleep(15)


def main() -> None:
    require_container()
    config = environment()
    seed_account(config)
    demo = Demo.load()
    print(demo.verify_inventory())
    demo.reset_lab()
    publish_portal(demo)
    print(demo.weather())
    print(demo.protection())
    print(f"Preflight traffic run ID: {demo.run_id}")
    cli("azd", "env", "set", "PREFLIGHT_RUN_ID", demo.run_id)
    print("Seed complete. Run python scripts/preflight.py --live --wait-telemetry --ai before presenting.")
    print("Publication HTTP readiness is not proof of browser sign-in/Try it: complete docs/setup.md.")


if __name__ == "__main__":
    main()
