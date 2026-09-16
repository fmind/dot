# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["google-antigravity==0.1.16"]
# ///
"""Fan work out to static subagents under explicit budgets and an explicit policy.

Set `ANTIGRAVITY_MODEL` and `ANTIGRAVITY_SDK_API_KEY` (or `GEMINI_API_KEY`) in the environment,
then run `uv run orchestrator.py <workspace>`;
every knob below is the orchestration contract, so change it here rather than in the prompt.
"""

import asyncio
import os
import pathlib
import sys

import pydantic
from google.antigravity import Agent, LocalAgentConfig, hooks, policy, types


class Audit(pydantic.BaseModel):
    """Typed contract for the orchestrator's answer."""

    findings: list[str]
    verdict: str


def record_finding(area: str, detail: str) -> str:
    """Records one audit finding for the given area."""
    # Custom Python tools bypass the policy engine entirely -- it gates built-ins
    # such as run_command and edit_file -- so they must stay side-effect free.
    print(f"finding_recorded area_chars={len(area)} detail_chars={len(detail)}", file=sys.stderr)
    return "recorded"


@hooks.pre_turn
async def trace_turn(_prompt: types.Content) -> types.HookResult:
    """Record a turn boundary without copying private prompt content."""
    print("turn_started", file=sys.stderr)
    return types.HookResult(allow=True)


READER = types.SubagentConfig(
    name="reader",
    description="Reads source files and reports what a module does.",
    system_instructions="Summarize behavior only. Never propose edits.",
    tools=[],
)

CRITIC = types.SubagentConfig(
    name="critic",
    description="Refutes a claimed finding using the source as evidence.",
    system_instructions="Default to refuting. Confirm only with a file and line.",
    tools=[record_finding],
)


def build(workspace: str) -> LocalAgentConfig:
    """Assembles the orchestrator: one parent, two isolated subagents."""
    path = pathlib.Path(workspace).resolve(strict=True)
    if not path.is_dir():
        raise ValueError("workspace must be an existing directory")
    root = str(path)
    model = os.environ.get("ANTIGRAVITY_MODEL", "").strip()
    if not model:
        raise ValueError("set ANTIGRAVITY_MODEL to a model available to your API project")
    api_key = os.environ.get("ANTIGRAVITY_SDK_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("set ANTIGRAVITY_SDK_API_KEY or GEMINI_API_KEY")
    return LocalAgentConfig(
        model=model,
        api_key=api_key,
        workspaces=[root],
        tools=[record_finding],  # subagent tools must also be registered here
        subagents=[READER, CRITIC],
        capabilities=types.CapabilitiesConfig(
            enable_subagents=True,
            allowed_subagents=["reader", "critic"],
            max_subagent_depth=1,  # without this, delegation nests without bound
            # read_only() omits START_SUBAGENT: filtering to it alone silently
            # disables delegation and rejects max_subagent_depth at validation.
            enabled_tools=[
                *types.BuiltinTools.read_only(),
                types.BuiltinTools.START_SUBAGENT,
            ],
        ),
        # Session budgets complement the caller deadline; policies select tools.
        budget_config=types.BudgetConfig(max_model_calls=40, max_tool_calls=80, max_total_tokens=400_000),
        # Unattended runs must not use policy.safe_defaults(handler): it routes
        # non-read-only tools to a handler that may wait for a human.
        policies=[
            policy.deny_all(),
            policy.allow(types.BuiltinTools.START_SUBAGENT.value),
            *[policy.allow(tool.value) for tool in types.BuiltinTools.read_only()],
            *policy.workspace_only([root]),
            policy.deny(types.BuiltinTools.RUN_COMMAND.value),
        ],
        hooks=[trace_turn],
        response_schema=Audit,
    )


async def main(workspace: str) -> None:
    """Runs one orchestration and prints the typed result."""
    async with Agent(build(workspace)) as agent:
        async def run() -> Audit:
            response = await agent.chat(
                "Delegate to reader for each top-level package, then have critic refute"
                " every claim. Report only surviving findings."
            )
            payload = await response.structured_output()
            if response.stop_reason != types.StopReason.UNSPECIFIED:
                raise RuntimeError(f"audit stopped before completion: {response.stop_reason.value}")
            result = Audit.model_validate(payload)
            if response.usage_metadata:
                print(f"tokens: {response.usage_metadata.total_token_count}", file=sys.stderr)
            return result

        result = await asyncio.wait_for(run(), timeout=300)
        print(result.verdict)
        for finding in result.findings:
            print(f"- {finding}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "."))
