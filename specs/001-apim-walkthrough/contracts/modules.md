# Module contract

| Module | Entry | Owned mutation | Verification | Exit/reset |
| --- | --- | --- | --- | --- |
| Portal | Published baseline and account | Second signup/subscription | Catalog, Try it, verification or defer | Sign out |
| Protection | Own setup | Lab counters only | 401, 400, 200, bounded 429 | Counter expires |
| Policies/tags | Own setup/lab baseline | Presenter fragment and lab policy | X-Demo-Policy changes | Restore lab policy/fragments |
| Monitoring | Own setup | Bounded traffic | Live or labeled real preflight records | None |
| MCP | Seeded server plus live example | Extra presenter server | Initialize, discover, call, key denial | Seeded server unchanged |
| AI | Own setup/model permission | None | Real tool call and grounded answer | No earlier module needed |

Each section has its own setup cell. No synthetic weather, fabricated assistant
answer, or silent skip is an acceptable result.
