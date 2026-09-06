# Git History Investigation

1. **Frame the question**: Name the repository, tracked path, line range or symbol, proposed change, and the specific uncertainty; keep the scope small enough that every cited commit can be inspected.
1. **Establish coverage**: Use `git` to record branch, `HEAD`, dirty state, available refs, and whether the clone is shallow; say which evidence Git cannot supply when the path is untracked, generated, vendored, or absent at `HEAD`. Preserve staged, unstaged, and untracked work.

   ```bash
   git status --short
   git rev-parse HEAD
   git rev-parse --is-shallow-repository
   ```

1. **Seed line provenance**: Treat movement and copy detection as clues, not guarantees; review a repository-owned `.git-blame-ignore-revs` before honoring it and disclose ignored revisions.

   ```bash
   git blame --line-porcelain -w -M -C -C -C -L <start>,<end> -- <path>
   ```

1. **Trace the timeline**: Use the smallest relevant view and name the exact revision range instead of treating every ref as one lineage.

   ```bash
   git log --follow --format=fuller -- <path>   # one file across renames
   git log -L <start>,<end>:<path>              # commits that shaped a line range
   git log -S '<literal>' -p -- <path>          # occurrence count of a string changed
   git log -G '<regex>' -p -- <path>            # a diff added or removed matching lines
   ```

1. **Inspect candidate commits**: Read subject, body, changed tests, schemas, migrations, configuration, and docs together; preserve reverts and behavior changes, and group mechanical edits only after verifying they are mechanical.

   ```bash
   git show --format=fuller --find-renames --find-copies --stat <sha>
   ```

1. **Resolve ancestry anomalies**: Check renames, splits, copies, bulk formatting, generated files, squashes, rebases, cherry-picks, backports, merge parents, and revert pairs; when line history stops at a rewrite, compare file history, pickaxe searches, and neighboring tests, and report the break rather than forcing one origin.
1. **Find coupling clues**: Count files that repeatedly changed with the target across behavior commits. Repeated co-change can suggest a test, schema, migration, or deployment constraint; one shared commit or a formatting sweep proves nothing.
1. **Add remote rationale only when needed**: Map an exact commit to its pull requests with `gh`, then read the PR body, linked issue, reviews, inline comments, and changed files; paginate, disclose truncation, and treat a title match or semantic search alone as low confidence.
1. **Extract decision atoms**: Separate facts, author-stated rationale, inference, contradiction, and unknowns; cite the commit, patch, test, issue, or review for every proposed constraint and check whether later changes superseded it.
1. **Return the history note**: Do not implement the change unless requested separately. Report:
   - **Bottom line**: the most likely explanation, its confidence, and whether it changes the proposed plan.
   - **Scope and identity**: `HEAD`, working-copy boundary, path, lines or symbol, revision range, shallow state, and remote evidence checked.
   - **Origin and timeline**: introducing evidence, later changes, fixes, reverts, and moves with short hashes and dates.
   - **Decision atoms and companion evidence**: each labeled fact, inference, contradiction, or unknown; co-changes stay correlation until code confirms the seam.
   - **Change risk**: what could break, which evidence may be stale, and the smallest current test or human answer that resolves the rest.
   - **Evidence sources**: local objects, remote discussion, runtime behavior, and human intent kept separate.
