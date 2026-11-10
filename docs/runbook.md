# Presenter runbook

**Presentation ceiling: 60 minutes.** The allocations below are fixed segment
budgets, not implementation estimates. Setup, provisioning, seeding, and first
telemetry ingestion are excluded.

| Order | Segment | Budget | Stop/skip point |
| --- | --- | --- | --- |
| 0 | Orient: architecture and live Azure gateway | 3 minutes | No command execution required |
| 1 | Developer portal, seeded user, and separate signup | 10 minutes | Defer verification if email is delayed |
| 2 | Endpoint protection | 10 minutes | After 401/400/200/429 evidence |
| 3 | Policies, fragments, API tags, Spec Kit | 10 minutes | Restore lab policy; presenter fragment may remain |
| 4 | Monitoring and investigation | 8 minutes | After gateway and backend correlation |
| 5 | REST-to-MCP | 9 minutes | Seeded server works if creation is skipped |
| 6 | Lightweight notebook AI assistant | 5 minutes | After real tool call and grounded answer |
| - | Discussion/variation buffer | 5 minutes | End at 60 minutes |

## Before sharing your screen

- Complete [setup and live acceptance](setup.md), not just Bicep compilation.
- Open tabs for the Azure APIM instance, consumer developer portal, Application
  Insights, and [the notebook](../notebooks/walkthrough.ipynb) in the DevContainer.
- Keep credentials, sign-in notifications, and email off the shared display.
- Have the seeded login ready and a second email account/private browser session.
- Record the genuine `PREFLIGHT_RUN_ID` for log-ingestion lag.
- Select the exact modules you will show. No module requires a prior module's
  live changes or notebook variables.

## Stage narrative

1. **Orient:** "The public API remains public. Our gateway adds a governed
   consumer contract, scoped access, policy, telemetry, and tool exposure."
2. **Developer portal:** "Discovery, documentation, subscriptions, and Try it
   reduce developer friction. Signup is independent of the seeded experience."
3. **Protection:** "Enforce access and request shape before backend execution;
   throttle on an isolated probe rather than abusing a public service."
4. **Development:** "Policies compose by scope; fragments reuse behavior.
   API tags aid discovery. Spec Kit makes AI-assisted changes reviewable."
5. **Observe:** "Distinguish gateway rejection from upstream failure. Show
   evidence, not merely that a logger resource exists."
6. **MCP:** "Selected existing operations become tools without hosting a
   custom MCP application. The gateway boundary still requires authentication."
7. **AI:** "The model chooses a tool; the notebook executes it through APIM;
   the final answer is grounded in the actual result. AI is the short finale."

Use [the detailed module guide](modules.md). Do not use Run All in the notebook.
Run each setup cell again after a kernel restart or when jumping modules.

## Shorter presentations

Remove entire segments, not prerequisites:

- Security emphasis: orientation, protection, policy authoring, monitoring.
- Developer emphasis: orientation, portal, policy authoring, MCP.
- Tool enablement: orientation, portal, MCP, optional assistant.

The seeded portal, account, fragments, monitoring, and MCP always remain.
If time is tight, inspect the seeded MCP and skip creating the extra server;
the AI segment still works. If model access fails, explicitly omit the assistant
and retain the protocol-level MCP demonstration.

## Finish

Stop within the ceiling. Clear saved notebook outputs. Do not tear down on stage.
After the event, use the explicit [cleanup procedure](troubleshooting.md#cleanup).
