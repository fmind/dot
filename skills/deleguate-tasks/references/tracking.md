# Tracking and Execution

Use the coordinator's native process tools and ordinary files. This workflow does not require an SDK, service, MCP server, or permanent background daemon.

## Local run directory

Create a uniquely named run under `~/.local/state/deleguate-tasks/` with a timestamp and random suffix; use directory mode `0700` and private files. Keep `ledger.json` and one directory per task containing `brief.md`, attempt-specific stdout/stderr, and the compact result. Record the absolute workspace separately. Do not place private briefs in version control.

The coordinator creates and updates JSON with a structured writer such as Python, using temporary-file replacement for ledger updates. Workers never edit the ledger. This is a schema example; populate real values rather than executing it:

```json
{
  "version": 1,
  "run_id": "timestamp-random",
  "tasks": [
    {
      "id": "task-1",
      "objective": "Investigate the failing parser test",
      "depends_on": [],
      "harness": "agy",
      "model": "gemini-3.8-flash-high",
      "effort": "high",
      "workspace": "/absolute/workspace",
      "baseline": { "revision": "commit-id", "dirty_snapshot": null },
      "state": "queued",
      "attempts": [],
      "verification": null
    }
  ]
}
```

For each attempt, record its number, start/end timestamps, exact argument list, process handle type/value, conversation ID, stdout/stderr paths, exit code, provider status, and error summary. Record handles locally; never assume a host handle is an OS PID or that a PID still belongs to this run after a restart. Preserve prior attempts on retries. Store reported usage with its scope: resumed agy sessions can report cumulative counters, so do not sum those counters as independent calls.

Use `queued`, `running`, `awaiting_verification`, `completed`, `blocked`, `failed`, and `canceled`. Move to `awaiting_verification` only after the process has ended and its result is parsed. Missing auth/quota/permissions or a failed dependency blocks the affected task. A crash or invalid result fails the attempt. On interruption, leave an uncertain process `running` until reconciled; do not relaunch it merely because a new coordinator cannot access the old handle. Release dependent tasks only after their prerequisites are verified and their artifacts are accessible in the dependent workspace.

## agy execution

Check `agy --version`, `agy --help`, and `agy models` before relying on a model or flag. Authenticate through the existing native session. The default model is `gemini-3.8-flash-high`; if unavailable, report the available choices without quietly substituting one.

For a single task, use this argument shape in the assigned workspace, replacing the example brief with the actual bounded task:

```bash
agy -p "Read the assigned brief and complete only its task. Return the requested evidence." \
  --model gemini-3.8-flash-high \
  --effort high \
  --output-format json \
  --print-timeout 15m
```

Pass the full brief as one argument with a subprocess argument list, or name a readable absolute brief path explicitly. Do not concatenate task text into shell code. Capture stdout and stderr to the attempt's files, and retain the host's process handle for polling and cancellation. With Python, use `subprocess.Popen` with an argument list and `cwd`, not `shell=True`; a foreground helper must remain responsible for its child until completion or cancellation. On timeout, terminate and reap owned processes and verify no worker remains before retrying; a wait timeout alone is not proof of cancellation.

Use `--conversation <recorded-id>` for a follow-up. For incremental events or an ongoing conversation, use the documented `--input-format stream-json --output-format stream-json` interface; send the next turn only after the current result. Parse the stream to disk rather than feeding every tool event into the coordinator's context.

Honor the child's own permissions. Headless agy can soft-deny a required tool, produce a response, and exit zero; inspect diagnostics and acceptance evidence as well as `status`. Workspace writes may be allowed by default, so a prompt saying "read only" is not enforcement. Use actual permission restrictions when read-only execution is required; never add `--dangerously-skip-permissions` merely to make automation run.

Do not treat `WAITING`, `RUNNING`, or missing/malformed JSON as completion. Record `ERROR`, `CANCELED`, `INTERRUPTED`, and `INVALID` distinctly in the attempt even when mapping them to the ledger's simpler states. Quota exhaustion is a blocker, not a reason to enable API keys or credit fallback. Retry a transient failure only after diagnosing it and checking for partial writes; cap automatic retries at one per task unless the user says otherwise.

## Worker return contract

Ask for a concise summary (normally at most 400 words), changed files or artifact paths, verification commands and outcomes, blockers, and remaining uncertainty. For edits, require the actual diff in the assigned workspace; for investigation, require concrete file/line evidence. Keep detailed logs in the run directory. `--json-schema` may constrain the worker's answer when a machine-readable payload is useful; the outer envelope still carries process/session metadata.

The coordinator records its own acceptance result in `verification`, including checks and unresolved limits. Do not repeat the entire investigation just to accept the task, and do not accept it solely because the worker says it succeeded.
