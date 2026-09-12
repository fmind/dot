---
name: a2a-python-sdk
description: Implement agent interoperability with the official A2A Python SDK and a2a CLI. Use for Agent Cards, clients, executors, task lifecycle, streaming, and cancellation.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/a2a-python-sdk
  created: "2026-09-10"
  updated: "2026-09-11"
---

# A2A Python SDK

Use the official `a2aproject/a2a-python` distribution `a2a-sdk` and the `a2aproject/a2a-cli` client `a2a`; [mcp-server](../mcp-server/SKILL.md) owns MCP tools/resources and [api-client](../api-client/SKILL.md) owns ordinary HTTP clients.

## Workflow

1. Inspect the locked SDK and supported protocol version. Install `uv add a2a-sdk` for a client, or `uv add "a2a-sdk[http-server]"` for the HTTP server integration; add other extras only when required. Use `a2a` to inspect remote agent endpoints and validate configuration.
1. Choose the transport supported by both peers and read that version's official sample. Construct an Agent Card with accurate capabilities, endpoints, security schemes, and advertised protocol skills.
1. Implement the SDK's agent executor and request handler, mapping execution to task states and artifacts. Preserve task/context identifiers, persist long-lived state, and implement cancellation of downstream work.
1. Build the client through the current client factory and card resolver APIs; inspect the locked implementation before adapting samples that use an older client class.
1. Verify a local client/server round trip with a deterministic executor or the `a2a` CLI: card discovery (`a2a card get`), message exchange (`a2a send`), task completion, invalid input, streaming when advertised (`a2a send --stream`), cancellation (`a2a task cancel`), and unknown task IDs.
1. Authenticate peers and authorize every task read/write by caller; enforce timeouts and size limits. Validate advertised endpoints and callback destinations before outbound requests, and test reconnect/retry without duplicate work.

## Gotchas

- SDK 1.x uses protobuf message types and route builders; older Pydantic models and `A2AStarletteApplication` examples target a different API. Match the `A2A-Version` request header to the peer's supported protocol version and test a mismatch.
- An Agent Card's `AgentSkill` advertises a protocol capability; it is not an Agent Skills `SKILL.md` package or proof of authorization.
- Do not advertise streaming, push notifications, or cancellation until the server implements and tests them.
- In-memory task storage is a local fixture; it does not prove restart recovery or support multiple server processes.

## Official Skills

The official [a2aproject/a2a-cli](https://github.com/a2aproject/a2a-cli) repository provides the `a2a-cli` Agent Skill (`skills/a2a-cli/SKILL.md`) to drive and test A2A agents from the command line, installable with `skills add a2aproject/a2a-cli --skill a2a-cli` or via its agent plugin. The official [a2aproject/a2a-python](https://github.com/a2aproject/a2a-python) repository contains contributor `mistake-reflection` guidance, not a consumer SDK skill in the inspected tree. Use its SDK docs and samples; do not confuse Agent Card skills with installable authoring guidance.

## Documentation

- [Official SDK](https://github.com/a2aproject/a2a-python) · [SDK documentation](https://a2a-protocol.org/latest/sdk/python/) · [A2A CLI](https://github.com/a2aproject/a2a-cli) · [Python tutorial](https://a2a-protocol.org/latest/tutorials/python/1-introduction/)
- Releases: [a2a-python](https://github.com/a2aproject/a2a-python/releases) · [changelog](https://github.com/a2aproject/a2a-python/blob/main/CHANGELOG.md)
