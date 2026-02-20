# Threat Model (MVP draft)

## Method

STRIDE-based threat modeling for gateway, policy, and audit paths.

## Initial STRIDE Matrix

- Spoofing: fake agent identity calling tool APIs
  - Mitigation: signed tokens for users/agents, identity binding in policy input (Iteration 3+)
- Tampering: modifying historical audit entries
  - Mitigation: immutable storage in immudb + hash chain verification (Iteration 2)
- Repudiation: actor denies sensitive action
  - Mitigation: mandatory audit for sensitive actions with actor metadata
- Information Disclosure: excessive room history exposed to agent
  - Mitigation: OPA checks + max context limits + purpose binding (Iteration 3/5)
- Denial of Service: flooding tool endpoint
  - Mitigation: rate limiting and bounded request sizes
- Elevation of Privilege: agent bypasses revoke and keeps reading room data
  - Mitigation: policy check before every access + revoke writes deny evidence

## Security Baselines Enabled in Iteration 1

- Explicit dependency health checks
- Request timeout and retry hooks in gateway clients
- Centralized config through environment variables
