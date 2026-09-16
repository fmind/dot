# Batch Manifest and Results

Write one JSON manifest and invoke the packaged runner with Python 3.12+ on Linux/macOS. Do not generate orchestration code or duplicate its ledger. Use a unique local manifest path outside worker workspaces; ordinary successful runs need only this contract and the final stdout result.

```json
{
  "concurrency": 2,
  "timeout": 900,
  "tasks": [
    {
      "id": "fix-parser",
      "workspace": "/absolute/project",
      "prompt": "Fix the parser's empty-input handling. Preserve existing work and tests; edit parser.py only. Run the existing parser tests. Do not commit.",
      "checks": [["python", "-m", "unittest", "test_parser"]]
    },
    {
      "id": "review-parser",
      "workspace": "/absolute/project",
      "depends_on": ["fix-parser"],
      "prompt": "Review parser.py and its tests for remaining edge cases. Return concise findings with file/line evidence; do not edit files."
    }
  ]
}
```

```bash
python ~/.agents/skills/deleguate-tasks/scripts/run.py /absolute/batch.json
```

## Contract

- `tasks`: 1–100 objects with unique lowercase `id` (letters/digits/hyphens), existing `workspace`, and nonempty `prompt`. Include required context, authorized changes, and relevant instructions in the prompt. The runner adds no-recursion and compact-response instructions.
- `concurrency`: default 2, range 1–16. Overlapping workspace paths (including symlink aliases and `add_dirs`) serialize even if more slots are available. Distinct paths are not a sandbox or proof that workers cannot reach shared resources; isolate actual writes before delegating.
- `timeout`: default 900 seconds, range 1–86400, applied separately to each worker and each acceptance command. Set a smaller bound for tests. Runtime has no automatic retry or quota fallback.
- `depends_on`: task IDs, default empty. Unknown dependencies and cycles fail before any launch. Dependents start only after all prerequisites reach `verified`.
- `checks`: argument lists run by the runner in the task workspace after successful worker completion. No shell expansion or interpolation. Prefer existing tests or a small coordinator-owned acceptance script outside worker write scope. Commands execute with coordinator authority; never adopt a worker-provided command unchecked. Protect tests from modification when their integrity matters. Their pass/fail is only as meaningful as their coverage.
- agy options: `model` defaults to `gemini-3.8-flash-high`, `effort` to `high`; optional `add_dirs` and `conversation_id`. `add_dirs` expands workspace access, not read-only enforcement. Do not include credentials. The native command uses `-p`, JSON output, a timeout, and disabled slash expansion; existing authentication/permissions remain in force.
- Other harnesses: `command` is an explicit argument list containing exactly one standalone `"{prompt}"` argument. Example: `["claude", "-p", "{prompt}", "--output-format", "text"]`. Put model/resume/access options directly in that command; do not combine it with agy-specific fields. Default `result_format` is `text`, where zero exit plus nonempty output permits independent checks; `agy-json` additionally requires an object with `status: SUCCESS` and a nonempty `response`. No native provider-status interpretation is claimed for custom text commands.

Unknown fields and invalid types fail before launch. Paths expand `~` and resolve against the runner's working directory; prefer absolute paths. Workers and checks receive no interactive stdin. Do not use commands that detach into a new OS session: cancellation owns the process group, not arbitrary daemons or remote jobs.

## Results and review

Stdout is one compact JSON object: `run` and a task list containing `id`, `state`, at most 600 characters of worker summary, `checks_passed`, `details`, and a failure message when applicable. No tool events, full transcripts, or polling chatter enter the parent context. Ask the host process tool to wait or notify on completion rather than reimplementing a monitor.

States: `queued` → `running` → `checking` → `verified` or `needs_review`; failures become `failed`, their dependents `blocked`, and stopped work `canceled`. A task without checks is `needs_review`. Any worker stderr also requires review, even if checks pass, because headless permission denials may accompany exit zero. A provider `WAITING`, `RUNNING`, or other non-success status never releases dependents. Exit 0 means all tasks verified, 1 means at least one unresolved task, and 2 means invalid input or an infrastructure error.

`verified` means supplied acceptance commands passed, not that an agent's claim is trusted or the user approved the result. Review changed code and evidence once when judgment is required. For investigations, leave checks empty and review the summary/findings; the runner will not fabricate verification.

## Records, cancellation, and continuation

Each invocation creates a private unique directory under `~/.local/state/deleguate-tasks/` (override with `--state-dir`). It saves the resolved `manifest.json`, atomic `ledger.json`, compact `result.json`, and per-task brief, worker stdout/stderr, and acceptance stdout/stderr. The ledger records command arguments, owned process IDs, machine timestamps, exit/provider status, native conversation ID, and reported usage. Saved agy usage may be cumulative on resumed conversations; do not sum cumulative counters as separate calls.

The runner stays responsible for its children until exit. SIGINT/SIGTERM cancels active tasks, terminates their owned process groups, and prevents queued tasks from starting. Timeout terminates the process group and fails that task. Normal completion also terminates descendants left in the worker's group. Hard kills, OS crashes, newly detached sessions, and remote work require manual reconciliation; never assume the saved ledger proves that such processes stopped.

For follow-up work or a retry, confirm the old runner exited, inspect partial changes and the relevant task's evidence, then create a new manifest. Use the task's recorded agy `conversation_id` when retaining context is appropriate. A new run directory preserves old attempts; never overwrite a previous ledger or use `--continue` to select a shared latest conversation. If a prerequisite needed human review, include its accepted artifacts in the new task prompt instead of depending on an ID from another batch.

Keep evidence private and outside version control. Preserve useful results; delete only task-owned disposable workspaces and redundant logs after successful integration. This runner does not create, merge, or delete worktrees, alter permissions, enable credit fallback, or install/authenticate harnesses.
