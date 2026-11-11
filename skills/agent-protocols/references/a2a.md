---
name: a2a
description: "A2A clients, servers, Agent Cards, task lifecycle, and official guidance."
---

# A2A Python SDK

Use official `a2a-sdk` (`a2aproject/a2a-python`) and the `a2a` CLI (`a2aproject/a2a-cli`); [MCP](mcp/GUIDE.md) owns tools/resources and [api-client](../../python-stack/references/api-client/GUIDE.md) owns plain HTTP clients.

## Workflow

1. **Pin SDK and protocol version**: `uv add a2a-sdk` (client) or `uv add "a2a-sdk[http-server]"` (HTTP server), adding extras only on demand; inspect remote peers with `a2a`.
1. **Define transport and Agent Card**: match a mutually supported transport from official samples and declare accurate capabilities, endpoints, security schemes, and protocol skills.
1. **Implement executor and handler**: map execution to task states and artifacts, preserve task/context IDs, persist durable state, and propagate cancellation downstream.
1. **Build clients via current factories**: use the locked SDK's client factory and card resolver rather than legacy client classes.
1. **Test a local round trip**: drive a deterministic executor or `a2a server --echo` (`--protocol 0.3` for legacy, `--proxy` logs live traffic to stderr—keep private) across `a2a card get`, `a2a send`, `a2a send --stream` (if advertised), `a2a task cancel`, invalid inputs, and unknown task IDs.
1. **Harden peers and egress**: authenticate peers, authorize every task read/write per caller, enforce timeouts/size caps, validate advertised/callback URLs before egress, and test idempotent retries.

## Gotchas

- **SDK 1.x API break**: 1.x uses protobuf messages and route builders (not older Pydantic/`A2AStarletteApplication` samples); align `A2A-Version` headers and test version mismatches.
- **`AgentSkill` != Agent Skill**: Agent Card `AgentSkill` entries advertise protocol capabilities, not `SKILL.md` packages or authorization.
- **Persist tasks**: in-memory stores fail restarts and multi-worker scaling—use `DatabaseTaskStore` (`a2a-sdk[postgresql]` or `[sqlite]`) plus 1.2 cluster mode (`a2a.server.cluster`) across replicas, testing restart and concurrency.

## Official Skills

[a2aproject/a2a-cli](https://github.com/a2aproject/a2a-cli) ships `a2a-cli` (`skills/a2a-cli/SKILL.md`), printable via `a2a skill` and installable via `DISABLE_TELEMETRY=1 skills add a2aproject/a2a-cli --skill a2a-cli` after review. [a2aproject/a2a-python](https://github.com/a2aproject/a2a-python) ships only contributor `mistake-reflection` guidance—use its SDK docs and samples instead.

## Documentation

- [Official SDK](https://github.com/a2aproject/a2a-python) · [SDK documentation](https://a2a-protocol.org/latest/sdk/python/) · [A2A CLI](https://github.com/a2aproject/a2a-cli) · [Python tutorial](https://a2a-protocol.org/latest/tutorials/python/1-introduction/)
- Releases: [a2a-python](https://github.com/a2aproject/a2a-python/releases) · [changelog](https://github.com/a2aproject/a2a-python/blob/main/CHANGELOG.md)
