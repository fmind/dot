# PyPI Publishing & Isolated Wheel Checks

- **Isolated wheel test**: export hashed runtime deps (`uv export --locked --no-dev --no-emit-project -o requirements.txt`—skip when `dependencies = []`), install into a fresh venv via `uv pip sync --require-hashes requirements.txt`, then run `uv pip install --no-deps <wheel>` and smoke-test imports/CLIs outside the repo.
- **Verified metadata**: set SPDX `license`, `license-files = ["LICENSE"]`, `readme = "README.md"`, `requires-python`, and `authors = [{ name = "<holder>" }]` (omit `email` unless verified/public on PyPI). OIDC Trusted Publishing verifies `github.com/<owner>/<slug>` (`Repository`, `Changelog`, `Issues`, `Security`) and `<owner>.github.io/<slug>/` plus **GitHub Statistics** (custom `Homepage` stays unverified).
- **Build & PEP 740 provenance**: run `uv build --clear --no-sources`, smoke-test the wheel outside the repo, and publish all artifacts together via [ci-cd](../../../../github/references/ci-cd/GUIDE.md) (`pypa/gh-action-pypi-publish`) for Full Provenance.
- **PEP 792 lifecycle**: yank broken versions with a reason instead of deleting files; archive retired PyPI projects alongside their GitHub repo.
