# Configuration entities

- Contract: complete paths/methods, upstream/normalized operation IDs, source URL,
  and SHA-256. No records are seeded into Weather.gov.
- Product: Weather, lab, and MCP; approval required for new subscribers.
- Developer: stable ID; private password only on first creation; active product
  subscription retains generated keys on seed reruns.
- Lab: intent validation, short-lived subscription counter, reusable response.
- MCP: three read-only tools referencing imported REST operations.
- Telemetry: actual gateway records and request/dependency correlation.
  Non-secret run IDs identify live/preflight traffic.
- Existing model: root endpoint/deployment name only; no persisted token/key or
  ownership of the external resource.
