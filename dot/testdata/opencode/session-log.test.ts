import type { PluginInput } from "@opencode-ai/plugin";
import { describe, expect, test } from "vitest";
import type { CommandRunner } from "../../../dot_config/opencode/plugins/session-log.ts";
import * as pluginModule from "../../../dot_config/opencode/plugins/session-log.ts";

async function loadHooks(run: CommandRunner, directory = ".") {
  // OpenCode invokes every runtime export as a plugin; test that exact boundary.
  expect(Object.keys(pluginModule)).toEqual(["default"]);
  const input = { $: run, directory } as unknown as PluginInput;
  const hooks = await pluginModule.default(input);
  if (!hooks.event) throw new Error("plugin must expose its event hook");
  return { event: hooks.event };
}

function recordingRunner(failAt = 0) {
  const calls: Array<{ strings: readonly string[]; values: string[] }> = [];
  const run: CommandRunner = async (strings, ...values) => {
    calls.push({ strings: [...strings], values });
    if (calls.length === failAt) throw new Error("synthetic command failure");
  };
  return { calls, run };
}

describe("OpenCode session-log plugin", () => {
  test("runs session ingestion before usage with literal values", async () => {
    const { calls, run } = recordingRunner();
    const hooks = await loadHooks(run, "/work/path with spaces");
    await hooks.event({ event: { type: "session.idle", properties: { sessionID: "session-1" } } });
    expect(calls).toHaveLength(2);
    expect(calls[0]?.values).toEqual(["session-1", "/work/path with spaces"]);
    expect(calls[1]?.values).toEqual(["session-1", "/work/path with spaces"]);
    expect(calls[0]?.strings.join("{}")).toContain("hook session opencode");
    expect(calls[1]?.strings.join("{}")).toContain("hook usage opencode");
  });

  test("uses the current directory default and ignores irrelevant events", async () => {
    const { calls, run } = recordingRunner();
    const hooks = await loadHooks(run);
    await hooks.event({ event: { type: "server.connected", properties: {} } });
    await hooks.event({ event: { type: "session.idle", properties: { sessionID: "session-2" } } });
    expect(calls).toHaveLength(2);
    expect(calls[0]?.values).toEqual(["session-2", "."]);
  });

  test("ignores an empty session id", async () => {
    const { calls, run } = recordingRunner();
    await (await loadHooks(run)).event({ event: { type: "session.idle", properties: { sessionID: "" } } });
    expect(calls).toHaveLength(0);
  });

  test("propagates rejection and does not run usage after ingestion fails", async () => {
    const { calls, run } = recordingRunner(1);
    const hooks = await loadHooks(run);
    await expect(
      hooks.event({ event: { type: "session.idle", properties: { sessionID: "session-3" } } }),
    ).rejects.toThrow("synthetic command failure");
    expect(calls).toHaveLength(1);
  });
});
