import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import xml.etree.ElementTree as ET

import httpx2 as httpx
import nbformat
from nbclient import NotebookClient
from jsonschema import ValidationError
import yaml
from mcp.types import CallToolResult, ListToolsResult, Tool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import demo as helpers
from build_notebook import build
from prepare_api import inventory

CONFIG = {
    "APIM_GATEWAY_URL": "https://demo.azure-api.net",
    "APIM_RESOURCE_ID": "/subscriptions/test/resourceGroups/demo/providers/Microsoft.ApiManagement/service/demo",
    "MCP_URL": "https://demo.azure-api.net/weather-mcp/mcp",
    "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
    "AZURE_OPENAI_DEPLOYMENT": "existing-model",
}


class ContractTests(unittest.TestCase):
    def test_complete_inventory_and_hash(self):
        text = (ROOT / "api/weather.openapi.json").read_text()
        recorded = json.loads((ROOT / "api/inventory.json").read_text())
        self.assertEqual(recorded["sha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(recorded["operations"], inventory(json.loads(text)))
        self.assertEqual(len(recorded["operations"]), 69)
        self.assertLess(len(text), 131072)
        self.assertTrue(recorded["compatibilityChanges"])

    def test_policy_scopes_and_credential_removal(self):
        for file in (ROOT / "policies").rglob("*.xml"):
            ET.parse(file)
        fragment = ET.parse(ROOT / "policies/fragments/weather-backend.xml").getroot()
        deleted = {n.attrib["name"] for n in fragment.findall("set-header") if n.attrib["exists-action"] == "delete"}
        self.assertEqual(deleted, {"Authorization", "Ocp-Apim-Subscription-Key"})
        self.assertEqual(fragment.find("set-query-parameter").attrib["exists-action"], "delete")
        for name in ("weather", "mcp", "lab"):
            self.assertIsNotNone(ET.parse(ROOT / f"policies/{name}.xml").find("inbound/base"))
        mcp_text = (ROOT / "policies/mcp.xml").read_text()
        self.assertNotIn("context.Response.Body", mcp_text)

    def test_seed_hook_and_streaming_safe_diagnostics(self):
        project = yaml.safe_load((ROOT / "azure.yaml").read_text())
        self.assertIn("postprovision", project["hooks"])
        self.assertNotIn("postdeploy", project["hooks"])
        self.assertNotIn("services", project)
        bicep = (ROOT / "infra/demo.bicep").read_text()
        self.assertIn("body: { bytes: 0 }", bicep)
        self.assertNotIn("headers: ['Authorization", bicep)

    def test_portal_try_it_cors_allows_default_request_headers(self):
        cors = ET.parse(ROOT / "policies/global.xml").find("inbound/cors")
        allowed = {header.text.lower() for header in cors.findall("allowed-headers/header")}
        self.assertTrue({
            "cache-control", "ocp-apim-subscription-key", "x-ms-client-request-id",
        }.issubset(allowed))
        self.assertEqual(cors.find("allowed-origins/origin").text, "__PORTAL_ORIGIN__")
        self.assertNotIn("*", allowed)

    def test_mcp_bindings_use_exact_imported_operation_ids(self):
        contract = json.loads((ROOT / "api/weather.apim.openapi.json").read_text())
        bicep = (ROOT / "infra/demo.bicep").read_text()
        bindings = dict(re.findall(r"name: '(weather_\w+)', operation: '([^']+)'", bicep))
        paths = {
            "weather_point": "/points/{latitude},{longitude}",
            "weather_forecast": "/gridpoints/{wfo}/{x},{y}/forecast",
            "weather_alerts": "/alerts/active/area/{area}",
        }
        self.assertEqual(set(bindings), set(paths))
        for tool, path in paths.items():
            with self.subTest(tool=tool):
                self.assertEqual(bindings[tool], contract["paths"][path]["get"]["operationId"])

    def test_inventory_preserves_operation_id_case_and_underscores(self):
        operations = inventory({"paths": {
            "/test": {"get": {"operationId": "MixedCase_operation"}},
        }})
        self.assertEqual(operations[0]["apimOperationId"], "MixedCase_operation")

    def test_forecast_url_routes_only_through_gateway(self):
        self.assertEqual(
            helpers.gateway_path("https://api.weather.gov/gridpoints/LWX/97,71/forecast"),
            "/weather/gridpoints/LWX/97,71/forecast",
        )
        for url in (
            "http://api.weather.gov/gridpoints/LWX/1,1/forecast",
            "https://api.weather.gov.evil/gridpoints/LWX/1,1/forecast",
            "https://user@api.weather.gov/gridpoints/LWX/1,1/forecast",
            "https://api.weather.gov:8443/gridpoints/LWX/1,1/forecast",
            "https://api.weather.gov/alerts",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                helpers.gateway_path(url)

    def test_document_links_exist(self):
        documents = [ROOT / "README.md", *list((ROOT / "docs").glob("*.md")),
                     *list((ROOT / "specs/001-apim-walkthrough").rglob("*.md"))]
        for file in documents:
            text = file.read_text()
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#"):
                    continue
                with self.subTest(document=file.name, target=target):
                    self.assertTrue((file.parent / target.split("#")[0]).exists())

    def test_notebook_empty_and_independent_entries(self):
        notebook = nbformat.read(ROOT / "notebooks/walkthrough.ipynb", as_version=4)
        nbformat.validate(notebook)
        self.assertEqual(notebook, build())
        entries = [c for c in notebook.cells if "module-entry" in c.metadata.get("tags", [])]
        self.assertEqual(len(entries), 6)
        for cell in notebook.cells:
            if cell.cell_type == "code":
                self.assertEqual(cell.outputs, [])
                self.assertIsNone(cell.execution_count)
                compile(cell.source, "<notebook>", "exec", flags=__import__("ast").PyCF_ALLOW_TOP_LEVEL_AWAIT)
        for entry in entries:
            with self.subTest(module=entry.metadata["tags"]):
                test = nbformat.v4.new_notebook(cells=[
                    nbformat.v4.new_code_cell(
                        f"import sys\nsys.path.insert(0, {str(ROOT)!r})\n"
                        "from unittest.mock import patch\nfrom types import SimpleNamespace\n"
                        "stub = patch('scripts.demo.Demo.load', return_value=SimpleNamespace(run_id='mock-local-test'))\n"
                        "stub.start()"
                    ), nbformat.v4.new_code_cell(entry.source),
                ])
                NotebookClient(test, timeout=30, kernel_name="python3").execute()


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.demo = helpers.Demo(CONFIG.copy(), "secret-not-for-output")

    def test_secret_repr(self):
        self.assertNotIn("secret-not-for-output", repr(self.demo))

    def test_inventory_verification_accepts_exact_source_ids(self):
        expected = json.loads((ROOT / "api/inventory.json").read_text())["operations"]
        operations = [{
            "name": item["sourceOperationId"],
            "properties": {"method": item["method"].upper(), "urlTemplate": item["path"]},
        } for item in expected]
        with patch.object(self.demo, "list_arm", return_value=operations):
            self.assertEqual(self.demo.verify_inventory(), {"paths_and_operations_verified": 69})

    def test_inventory_verification_rejects_ids_bound_to_wrong_paths(self):
        expected = json.loads((ROOT / "api/inventory.json").read_text())["operations"]
        operations = [{
            "name": item["apimOperationId"],
            "properties": {"method": item["method"].upper(), "urlTemplate": item["path"]},
        } for item in expected]
        operations[0]["name"], operations[1]["name"] = operations[1]["name"], operations[0]["name"]
        with patch.object(self.demo, "list_arm", return_value=operations):
            with self.assertRaisesRegex(RuntimeError, "operation IDs differ"):
                self.demo.verify_inventory()

    def test_arguments(self):
        schema = {"type": "object", "required": ["area"], "properties": {"area": {"enum": ["VA"]}}}
        helpers.validate_arguments("weather_alerts", {"area": "VA"}, schema)
        with self.assertRaises(ValueError):
            helpers.validate_arguments("unauthorized", {}, schema)
        with self.assertRaises(ValidationError):
            helpers.validate_arguments("weather_alerts", {"area": "invalid"}, schema)
        with self.assertRaises(ValueError):
            helpers.validate_arguments("weather_alerts", {"area": "x" * 5000}, schema)

    def test_sensitive_cli_failure_redacts_output(self):
        result = SimpleNamespace(returncode=1, stderr="secret-not-for-output", stdout="")
        with patch.dict(os.environ, {"APIM_DEMO_CONTAINER": "1"}), patch("demo.subprocess.run", return_value=result):
            with self.assertRaises(RuntimeError) as caught:
                helpers.cli("az", "rest", sensitive=True)
        self.assertNotIn("secret-not-for-output", str(caught.exception))

    def test_cli_normalizes_leading_bom_without_changing_other_output(self):
        for raw in ('\ufeff{"ok": true}\n', '{"ok": true}\n', "  plain text\n", ""):
            with self.subTest(raw=raw):
                result = SimpleNamespace(returncode=0, stderr="", stdout=raw)
                with patch.dict(os.environ, {"APIM_DEMO_CONTAINER": "1"}), \
                     patch("demo.subprocess.run", return_value=result):
                    output = helpers.cli("az", "rest")
                self.assertEqual(output, raw.removeprefix("\ufeff"))
                if "{" in output:
                    self.assertEqual(json.loads(output), {"ok": True})

    def test_host_execution_rejected(self):
        with patch.dict(os.environ, {"APIM_DEMO_CONTAINER": "0"}), self.assertRaises(RuntimeError):
            helpers.require_container()

    def test_gateway_request_never_places_key_in_query(self):
        with patch("demo.httpx.request", return_value=httpx.Response(200)) as send:
            self.demo.request("/lab/probe")
        self.assertNotIn("secret-not-for-output", send.call_args.args[1])
        self.assertEqual(send.call_args.kwargs["headers"]["Ocp-Apim-Subscription-Key"], "secret-not-for-output")

    def test_management_updates_use_etag_wildcard(self):
        with patch("demo.cli", return_value="{}") as run:
            self.demo.arm("apis/security-lab/policies/policy", method="put", body={"properties": {}})
        self.assertIn("If-Match=*", run.call_args.args)

    def test_management_requests_explicitly_negotiate_json(self):
        for method in ("get", "put"):
            with self.subTest(method=method), patch("demo.cli", return_value="{}") as run:
                self.demo.arm("apis/security-lab/policies/policy", method=method)
                self.assertIn("Accept=application/json", run.call_args.args)
                self.assertEqual(run.call_args.args.count("--headers"), 1)
                self.assertEqual("If-Match=*" in run.call_args.args, method == "put")

    def test_lab_burst_is_bounded_and_never_uses_weather(self):
        responses = [httpx.Response(code, json={"synthetic": True}) for code in (401, 401, 400, 200, 200, 429)]
        with patch.object(self.demo, "request", side_effect=responses) as send, patch("demo.time.sleep"):
            result = self.demo.protection()
        self.assertEqual([r["status"] for r in result], [401, 401, 400, 200, 429])
        self.assertTrue(all(c.args[0] == "/lab/probe" for c in send.call_args_list))

    def test_lab_reset_owns_only_lab(self):
        with patch.object(self.demo, "arm", return_value={}) as arm:
            self.demo.reset_lab()
        self.assertEqual([c.args[0] for c in arm.call_args_list], [
            "policyFragments/lab-protection", "policyFragments/lab-response",
            "apis/security-lab/policies/policy",
        ])

    def test_mcp_sdk_discovery_preserves_schema_dictionary_keys(self):
        tools = [
            Tool.model_validate({
                "name": name, "description": name,
                "inputSchema": {"type": "object", "properties": {"area": {"type": "string"}}},
            })
            for name in sorted(helpers.ALLOWED_TOOLS)
        ]
        session = SimpleNamespace(
            list_tools=AsyncMock(return_value=ListToolsResult(tools=tools)),
        )
        async def run(action):
            return await action(session)
        with patch.object(self.demo, "mcp_session", side_effect=run):
            discovered = asyncio.run(self.demo.mcp_tools())
        self.assertEqual({tool["name"] for tool in discovered}, helpers.ALLOWED_TOOLS)
        self.assertEqual(discovered[0]["inputSchema"], tools[0].input_schema)

    def test_mcp_sdk_successful_call_preserves_wire_result_keys(self):
        result = CallToolResult.model_validate({
            "content": [{"type": "text", "text": '{"city":"Washington"}'}],
            "structuredContent": {"city": "Washington"}, "isError": False,
        })
        session = SimpleNamespace(
            list_tools=AsyncMock(return_value=ListToolsResult(tools=[
                Tool.model_validate({"name": "weather_point", "inputSchema": {"type": "object"}}),
            ])),
            call_tool=AsyncMock(return_value=result),
        )
        async def run(action):
            return await action(session)
        with patch.object(self.demo, "mcp_session", side_effect=run):
            actual = asyncio.run(self.demo.mcp_call("weather_point", {}))
        self.assertEqual(actual["structuredContent"], {"city": "Washington"})
        self.assertFalse(actual["isError"])
        session.call_tool.assert_awaited_once_with("weather_point", arguments={})

    def test_mcp_sdk_tool_error_is_not_a_success(self):
        session = SimpleNamespace(
            list_tools=AsyncMock(return_value=ListToolsResult(tools=[
                Tool.model_validate({"name": "weather_point", "inputSchema": {"type": "object"}})
            ])),
            call_tool=AsyncMock(return_value=CallToolResult.model_validate({"content": [], "isError": True})),
        )
        async def run(action):
            return await action(session)
        with patch.object(self.demo, "mcp_session", side_effect=run):
            with self.assertRaisesRegex(RuntimeError, "reported an error"):
                asyncio.run(self.demo.mcp_call("weather_point", {}))

    def test_mcp_sdk_existing_weather_server_cell(self):
        import ast

        cell = next(c for c in build().cells if "seeded-server-proof" in c.metadata.get("tags", []))
        for is_error in (False, True):
            with self.subTest(is_error=is_error):
                result = CallToolResult.model_validate({"content": [], "isError": is_error})
                session = SimpleNamespace(
                    list_tools=AsyncMock(return_value=ListToolsResult(tools=[
                        Tool.model_validate({"name": name, "inputSchema": {"type": "object"}})
                        for name in ("weather_forecast", "weather_alerts", "weather_point")
                    ])),
                    call_tool=AsyncMock(return_value=result),
                )
                async def run(action):
                    self.assertEqual(self.demo.config["MCP_URL"], CONFIG["MCP_URL"])
                    return await action(session)
                namespace = {"demo": self.demo}
                compiled = compile(cell.source, "<seeded-server-proof>", "exec",
                                   flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
                with patch.object(self.demo, "mcp_session", side_effect=run), patch("builtins.print"):
                    if is_error:
                        with self.assertRaisesRegex(RuntimeError, "reported an error"):
                            asyncio.run(eval(compiled, namespace))
                    else:
                        asyncio.run(eval(compiled, namespace))
                session.call_tool.assert_awaited_once_with(
                    "weather_point", arguments={"latitude": 38.8894, "longitude": -77.0352},
                )
                self.assertEqual(self.demo.config["MCP_URL"], CONFIG["MCP_URL"])

    def test_assistant_requires_tool_and_bounds_turns(self):
        schema = [{"name": "weather_point", "description": "Point", "inputSchema": {"type": "object"}}]
        function_call = SimpleNamespace(
            id="call-1", function=SimpleNamespace(name="weather_point", arguments="{}"),
            model_dump=lambda **kwargs: {"id": "call-1", "type": "function",
                                        "function": {"name": "weather_point", "arguments": "{}"}},
        )
        message = SimpleNamespace(content=None, tool_calls=[function_call])
        response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        model = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=response))))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=model)
        context.__aexit__ = AsyncMock(return_value=False)
        credential = MagicMock()
        credential.__aenter__ = AsyncMock(return_value=credential)
        credential.__aexit__ = AsyncMock(return_value=False)
        with patch("openai.AsyncOpenAI", return_value=context), \
             patch("azure.identity.aio.AzureCliCredential", return_value=credential), \
             patch("azure.identity.aio.get_bearer_token_provider", return_value=AsyncMock(return_value="token")), \
             patch.object(self.demo, "mcp_tools", AsyncMock(return_value=schema)), \
             patch.object(self.demo, "mcp_call", AsyncMock(return_value={"result": "public data"})) as call:
            with self.assertRaisesRegex(RuntimeError, "three-turn"):
                asyncio.run(helpers.assistant(self.demo))
        self.assertEqual(model.chat.completions.create.await_count, 3)
        self.assertEqual(call.await_count, 3)
        from openai import NOT_GIVEN
        for request in model.chat.completions.create.await_args_list:
            self.assertIs(request.kwargs["reasoning_effort"], NOT_GIVEN)

    def test_assistant_rejects_non_azure_token_destination(self):
        self.demo.config["AZURE_OPENAI_ENDPOINT"] = "https://not-azure.example"
        with self.assertRaisesRegex(ValueError, "resource-root"):
            asyncio.run(helpers.assistant(self.demo))

    def test_assistant_notebook_displays_and_sends_same_prompt(self):
        import ast

        cell = next(c for c in build().cells if "assistant-demo" in c.metadata.get("tags", []))
        assistant = AsyncMock(return_value={
            "tool_calls": [{"name": "weather_point", "arguments": {}, "result": {}}],
            "answer": "Nearby city: Washington.",
        })
        namespace = {"demo": self.demo, "assistant": assistant, "asyncio": asyncio}
        compiled = compile(cell.source, "<assistant-demo>", "exec",
                           flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        with patch("builtins.print") as output:
            asyncio.run(eval(compiled, namespace))
        output.assert_any_call("System prompt:", helpers.ASSISTANT_SYSTEM_PROMPT)
        output.assert_any_call("User prompt:", helpers.ASSISTANT_USER_PROMPT)
        assistant.assert_awaited_once_with(self.demo, prompt=helpers.ASSISTANT_USER_PROMPT)

    def test_assistant_default_prompt_uses_city_name_without_coordinates(self):
        self.assertIn("Washington, DC, USA", helpers.ASSISTANT_USER_PROMPT)
        self.assertNotRegex(helpers.ASSISTANT_USER_PROMPT, r"\d")
        self.assertIn("infer approximate city-center coordinates", helpers.ASSISTANT_SYSTEM_PROMPT)
        self.assertIn("call weather_point", helpers.ASSISTANT_SYSTEM_PROMPT)
        self.assertIn("Ground weather and forecast-office details in tool results", helpers.ASSISTANT_SYSTEM_PROMPT)

    def test_assistant_rejects_invalid_reasoning_effort_before_network_calls(self):
        self.demo.config["AZURE_OPENAI_REASONING_EFFORT"] = "invalid"
        with patch.object(self.demo, "mcp_tools", AsyncMock()) as discover:
            with self.assertRaisesRegex(ValueError, "AZURE_OPENAI_REASONING_EFFORT"):
                asyncio.run(helpers.assistant(self.demo))
        discover.assert_not_awaited()

    def test_assistant_success_requires_real_tool_result(self):
        self.demo.config["AZURE_OPENAI_REASONING_EFFORT"] = "none"
        schemas = [{"name": "weather_point", "description": "Point", "inputSchema": {"type": "object"}}]
        call = SimpleNamespace(
            id="call-1", function=SimpleNamespace(name="weather_point", arguments="{}"),
            model_dump=lambda **kwargs: {"id": "call-1", "type": "function",
                                        "function": {"name": "weather_point", "arguments": "{}"}},
        )
        responses = [
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[call]))]),
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Nearby city: Washington.", tool_calls=[]))]),
        ]
        model = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(side_effect=responses))))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=model)
        context.__aexit__ = AsyncMock(return_value=False)
        credential = MagicMock()
        credential.__aenter__ = AsyncMock(return_value=credential)
        credential.__aexit__ = AsyncMock(return_value=False)
        public_result = {"content": [{"text": '{"city":"Washington"}'}]}
        with patch("openai.AsyncOpenAI", return_value=context), \
             patch("azure.identity.aio.AzureCliCredential", return_value=credential), \
             patch("azure.identity.aio.get_bearer_token_provider", return_value=AsyncMock(return_value="token")), \
             patch.object(self.demo, "mcp_tools", AsyncMock(return_value=schemas)), \
             patch.object(self.demo, "mcp_call", AsyncMock(return_value=public_result)):
            result = asyncio.run(helpers.assistant(self.demo))
        self.assertEqual(result["tool_calls"][0]["result"], public_result)
        self.assertEqual(result["answer"], "Nearby city: Washington.")
        self.assertEqual(result["run_id"], self.demo.run_id)
        self.assertNotIn("secret-not-for-output", json.dumps(result))
        for request in model.chat.completions.create.await_args_list:
            self.assertEqual(request.kwargs["reasoning_effort"], "none")
            self.assertEqual(request.kwargs["messages"][:2], [
                {"role": "system", "content": helpers.ASSISTANT_SYSTEM_PROMPT},
                {"role": "user", "content": helpers.ASSISTANT_USER_PROMPT},
            ])

    def test_seed_rerun_preserves_credentials_and_missing_partial_state(self):
        from seed import seed_account
        config = {**CONFIG, "DEMO_DEVELOPER_EMAIL": "demo@example.invalid", "APIM_NAME": "demo"}
        user = {"name": "demo-developer", "properties": {"email": config["DEMO_DEVELOPER_EMAIL"]}}
        subscription = {"name": "demo-presenter", "properties": {
            "scope": CONFIG["APIM_RESOURCE_ID"] + "/products/weather-demo",
            "ownerId": CONFIG["APIM_RESOURCE_ID"] + "/users/demo-developer", "state": "active",
        }}
        with patch("seed.Demo.list_arm", side_effect=[[user], [subscription]]), \
             patch("seed.deploy_template") as deploy, patch("seed.getpass.getpass") as password:
            seed_account(config)
            deploy.assert_not_called()
            password.assert_not_called()
        relative = {"name": "demo-presenter", "properties": {
            "scope": "/products/weather-demo", "ownerId": "/users/demo-developer", "state": "active",
        }}
        with patch("seed.Demo.list_arm", side_effect=[[user], [relative]]), \
             patch("seed.deploy_template") as deploy:
            seed_account(config)
            deploy.assert_not_called()
        with patch("seed.Demo.list_arm", side_effect=[[user], []]), \
             patch("seed.deploy_template") as deploy, patch("seed.getpass.getpass") as password:
            seed_account(config)
            self.assertFalse(deploy.call_args.args[2]["createUser"])
            self.assertTrue(deploy.call_args.args[2]["createSubscription"])
            password.assert_not_called()

    def test_seed_rejects_email_owned_by_another_user_before_prompting(self):
        from seed import seed_account
        config = {**CONFIG, "DEMO_DEVELOPER_EMAIL": "demo@example.invalid", "APIM_NAME": "demo"}
        other = {"name": "another-user", "properties": {"email": "DEMO@example.invalid"}}
        with patch("seed.Demo.list_arm", side_effect=[[other], []]), \
             patch("seed.deploy_template") as deploy, patch("seed.getpass.getpass") as password:
            with self.assertRaisesRegex(RuntimeError, "azd env set DEMO_DEVELOPER_EMAIL") as caught:
                seed_account(config)
            self.assertNotIn("demo@example.invalid", str(caught.exception).lower())
            password.assert_not_called()
            deploy.assert_not_called()

    def test_sensitive_seed_failure_has_safe_deployment_status_guidance(self):
        from seed import deploy_template
        with patch("seed.cli", side_effect=RuntimeError("secret-not-for-output")) as run:
            with self.assertRaisesRegex(RuntimeError, "seed-developer") as caught:
                deploy_template(
                    {"AZURE_RESOURCE_GROUP": "test-group"}, "developer",
                    {"password": "secret-not-for-output"}, sensitive=True,
                )
        message = str(caught.exception)
        self.assertIn("az deployment group show", message)
        self.assertIn("Running", message)
        self.assertNotIn("secret-not-for-output", message)
        self.assertTrue(caught.exception.__suppress_context__)
        args = run.call_args.args
        parameter_file = args[args.index("--parameters") + 1].removeprefix("@")
        self.assertFalse(Path(parameter_file).exists())
        self.assertTrue(run.call_args.kwargs["sensitive"])

    def test_nonsensitive_seed_failure_retains_original_error(self):
        from seed import deploy_template
        error = RuntimeError("Non-sensitive portal deployment failed")
        with patch("seed.cli", side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                deploy_template({"AZURE_RESOURCE_GROUP": "test-group"}, "portal", {})
        self.assertIs(caught.exception, error)


if __name__ == "__main__":
    unittest.main()
