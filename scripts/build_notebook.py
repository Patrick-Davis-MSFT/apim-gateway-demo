"""Reproduce the presenter notebook with no saved outputs or credentials."""

from pathlib import Path

import nbformat as nb

ROOT = Path(__file__).resolve().parents[1]

SETUP = """from pathlib import Path
import sys, asyncio
root = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "azure.yaml").exists())
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
from scripts.demo import Demo, assistant
demo = Demo.load()
print("This module's traffic:", demo.run_id)
"""


def build():
    cells = []

    def markdown(text):
        cells.append(nb.v4.new_markdown_cell(text))

    def code(text, tags=None):
        cell = nb.v4.new_code_cell(text)
        if tags:
            cell.metadata["tags"] = tags
        cells.append(cell)

    def entry(number, title, description):
        markdown(f"## M{number}. {title}\n\n{description}\n\nRun this section's setup even after restarting the kernel. No earlier module is required.")
        code(SETUP, ["module-entry", f"module-{number}"])

    markdown("""# APIM weather walkthrough

**Run inside the VS Code DevContainer against the pre-provisioned Azure APIM.**
Use [the runbook](../docs/runbook.md) and [portal instructions](../docs/modules.md).
Do not Run All during a presentation: choose modules and execute their cells visibly.
Model, keys, account signup, deployment, and log ingestion are preflight prerequisites.
Clear all outputs before saving/sharing. No subscription key is displayed.
""")
    entry(1, "Developer enablement", "Use the managed developer portal for catalog, sign-in, Try it, and independent second-account signup. This cell verifies the live REST path without replacing the browser walkthrough.")
    code("demo.verify_inventory()")
    code("demo.weather()")

    entry(2, "Endpoint protection", "Optional baseline reset is explicit below. All burst traffic is synthetic `/lab/probe`, never Weather.gov. Expect 401, 400, 200, then a bounded 429. Rate counters expire after ten seconds.")
    code("demo.reset_lab()\nprint('Only the lab policy and its two baseline fragments were restored.')")
    code("demo.protection()")

    entry(3, "Policies, fragments, and API tags", "Inspect tags and the reviewed Spec Kit artifacts. Follow the portal authoring steps to create `presenter-response` and include it on the **lab API only**. Never edit the Weather or seeded MCP API for this exercise.")
    code("demo.reset_lab()\nprint([(t['name'], t['properties']['displayName']) for t in demo.list_arm('tags')])")
    markdown("After completing the portal fragment edit, run the proof cell. If you skip authoring, skip this proof and continue to any other module.")
    code("""response = demo.request("/lab/probe")
demo.expect(response, 200, "Presenter fragment")
assert response.headers.get("X-Demo-Policy") == "presenter-fragment", "Include presenter-response in the lab policy first."
print(response.headers["X-Demo-Policy"], response.json())""", ["portal-edit-proof"])
    markdown("Explicit reset, if desired. The unreferenced presenter fragment can remain; it is not used by other modules.")
    code("demo.reset_lab()\nprint('Lab baseline restored; Weather/MCP unchanged.')")

    entry(4, "Monitoring and investigation", "Generate independent real traffic. Then use Azure Monitor and Application Insights in the Azure portal. Fresh ingestion may lag; the next cells clearly distinguish this run from real preflight traffic.")
    code("print(demo.weather())\nprint(demo.protection())")
    code("""query = f'''
ApiManagementGatewayLogs
| where TimeGenerated > ago(1d)
| where tostring(RequestHeaders) contains "{demo.run_id}"
| project TimeGenerated, ApiId, OperationId, ResponseCode, BackendResponseCode, TotalTime, CorrelationId
| order by TimeGenerated desc
'''
new_logs = demo.query(query)
if not new_logs["tables"][0]["rows"]:
    print("No records for THIS run yet. Use the explicitly labeled preflight cell or refresh after ingestion.")
new_logs""")
    code("""preflight_id = demo.config.get("PREFLIGHT_RUN_ID")
if not preflight_id:
    raise RuntimeError("No preflight run ID. Run azd hooks run postprovision before presenting.")
print("HISTORICAL REAL PREFLIGHT TRAFFIC, not this run:", preflight_id)
demo.query(query.replace(demo.run_id, preflight_id))""")
    code("""insights_id = (
    demo.config["APIM_RESOURCE_ID"].split("/providers/")[0]
    + "/providers/Microsoft.Insights/components/" + demo.config["APPLICATION_INSIGHTS_NAME"]
)
demo.query(f'''
AppRequests
| where TimeGenerated > ago(1d) and _ResourceId =~ "{insights_id}"
| project TimeGenerated, OperationId, RequestName=Name, ResultCode, Success, DurationMs
| join kind=leftouter (
    AppDependencies
    | where TimeGenerated > ago(1d)
    | project OperationId, DependencyName=Name, Target, BackendDurationMs=DurationMs
) on OperationId
| order by TimeGenerated desc
| take 20
''')""")

    entry(5, "Native REST-to-MCP", "The seeded native server is always available, even if live conversion is skipped. First inspect/create the additional server in the portal following the module guide. The SDK performs real MCP initialization, discovery, and tool calls.")
    code("""denial = demo.request("/weather-mcp/mcp", method="POST", key_mode="missing")
demo.expect(denial, 401, "MCP without subscription key")
print("MCP missing-key status:", denial.status_code)
await demo.mcp_tools()""")
    code("""result = await demo.mcp_call("weather_point", {"latitude": 38.8894, "longitude": -77.0352})
print(str(result)[:2500])""")
    markdown("Verify the existing `weather-mcp` server using the configured `MCP_URL`. It exposes three tools; select `weather_point` by name, not by position or tool count. No separate `presenter-mcp` server is required.")
    code("""discovered = await demo.mcp_tools()
point_tool = next(tool for tool in discovered if tool["name"] == "weather_point")
print("Existing server tool:", point_tool["name"], point_tool["inputSchema"])
result = await demo.mcp_call(point_tool["name"], {"latitude": 38.8894, "longitude": -77.0352})
print(str(result)[:2500])""", ["seeded-server-proof"])

    entry(6, "Lightweight AI assistant", "Uses the existing tool-capable Azure OpenAI model and your CLI identity. No model or agent is deployed. The default user prompt names Washington, DC, USA; the model infers approximate city-center coordinates for the point tool, not a live geocoding service. The assistant must call a real allowed MCP tool and ground its answer in that result. The point-only prompt avoids large alert collections.")
    markdown("### Prompts sent to the model\n\nThe next cell prints the exact **system prompt** (tool-use and safety instructions) and **user prompt** (the point lookup request) before calling the model. Both come from the same constants used by the assistant. To try a different request, replace `user_prompt` with your own text.\n\nThe request also includes the names, descriptions, and input schemas discovered from `weather-mcp` as function tools. After a tool call, its real result is added as a `tool` message so the model can produce a grounded answer; there is no separate hidden answer-generation prompt.")
    code("""from scripts.demo import ASSISTANT_SYSTEM_PROMPT, ASSISTANT_USER_PROMPT

user_prompt = ASSISTANT_USER_PROMPT
print("System prompt:", ASSISTANT_SYSTEM_PROMPT)
print("User prompt:", user_prompt)
answer = await asyncio.wait_for(assistant(demo, prompt=user_prompt), timeout=120)
print("Tool calls:", [{"name": c["name"], "arguments": c["arguments"]} for c in answer["tool_calls"]])
print("Real tool result preview:", str(answer["tool_calls"][0]["result"])[:1600])
print("Grounded answer:", answer["answer"])""", ["assistant-demo"])
    markdown("## Finish\n\nDo not run cleanup on stage. Follow the explicit teardown instructions after the event. Clear all notebook outputs before saving.")
    notebook = nb.v4.new_notebook(cells=cells)
    notebook.metadata["kernelspec"] = {"display_name": "Python 3 (DevContainer)", "language": "python", "name": "python3"}
    notebook.metadata["language_info"] = {"name": "python", "version": "3.12"}
    for index, cell in enumerate(cells):
        cell.id = f"walkthrough-{index:02d}"
    return notebook


if __name__ == "__main__":
    directory = ROOT / "notebooks"
    directory.mkdir(exist_ok=True)
    nb.write(build(), directory / "walkthrough.ipynb")
    print("Generated walkthrough notebook with independent entries and empty outputs.")
