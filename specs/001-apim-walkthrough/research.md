# Research decisions

| Decision | Rationale | Alternative not selected |
| --- | --- | --- |
| Complete snapshot | User selected full import; preserve all 69 operations | Curated REST subset |
| Compact unchanged JSON | Bicep loadTextContent has a 131072-character limit | Omit operations or mutable remote import |
| Native REST-backed MCP | APIM hosts protocol and selected tools | Local/custom MCP server |
| Preview only for MCP management | Current documented model uses 2025-09-01-preview | Undocumented resource shapes |
| Default managed portal and revision | Temporary deployment; no v2 content migration | Custom self-hosted portal |
| Synthetic protection API | Bounded throttling without hammering Weather.gov | Burst against upstream |
| Existing model and CLI identity | User approved; no new model deployment | Hosted agent/model |
| Current MCP/OpenAI APIs | CFS resolves MCP 2/OpenAI 3; async credentials/httpx2 | Assume older examples still apply |
| Zero-body diagnostics | Preserve streaming and avoid credentials | Full body logging |

Primary references:
[import](https://learn.microsoft.com/azure/api-management/api-management-api-import-restrictions),
[MCP](https://learn.microsoft.com/azure/api-management/manage-mcp-servers-rest-api),
[portal publication](https://learn.microsoft.com/rest/api/apimanagement/portal-revision/create-or-update),
[monitoring](https://learn.microsoft.com/azure/api-management/monitor-api-management),
[Spec Kit](https://github.com/github/spec-kit).
