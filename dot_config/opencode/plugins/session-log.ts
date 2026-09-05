import type { Plugin } from "@opencode-ai/plugin";

type EventHook = NonNullable<Awaited<ReturnType<Plugin>>["event"]>;
export type CommandRunner = (strings: TemplateStringsArray, ...values: string[]) => Promise<unknown>;

function createSessionLogHooks(run: CommandRunner, directory = ".") {
  const event: EventHook = async ({ event }) => {
    if (event.type !== "session.idle") return;
    const sid = event.properties.sessionID;
    if (!sid) return;
    await run`dot agent hook session opencode ${sid} ${directory}`;
    await run`dot agent hook usage opencode ${sid} ${directory}`;
  };
  return { event };
}

// OpenCode has no "session.idle" hook key: session events arrive through the
// generic `event` hook, and the payload is `{ type, properties }`, not `data`.
// The previous shape silently never ran. The working directory comes from the
// plugin input, since EventSessionIdle carries only a sessionID.
export default (async ({ $, directory }) => {
  const run: CommandRunner = async (strings, ...values) => $(strings, ...values);
  return createSessionLogHooks(run, directory);
}) satisfies Plugin;
