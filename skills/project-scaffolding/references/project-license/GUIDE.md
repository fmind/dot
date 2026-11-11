---
name: project-license
description: "Choose, write, and declare a repository LICENSE (MIT, CC-BY-4.0, or proprietary) by namespace and content."
---

# Project License

Select, write, and declare a repository's `LICENSE` from its namespace, visibility, and content; [repository](../../../gh/references/repository/GUIDE.md) owns GitHub settings, and [bootstrap](../bootstrap.md) calls this guide during scaffolding.

## Workflow

1. **Inspect namespace and existing license**: run `ls LICENSE*` and `gh repo view --json nameWithOwner,isPrivate,licenseInfo` (never print raw Git remotes, which may embed credentials). Keep any existing license unless asked to replace it.
1. **Select**:
   - Public `fmind` code: [MIT](templates/MIT) as `LICENSE`.
   - Written course material (lessons, exercises, prose, e.g., `fmind/mlops-coding-course`): CC-BY-4.0 as `LICENSE.txt` via `curl -fsSL https://creativecommons.org/licenses/by/4.0/legalcode.txt -o LICENSE.txt`.
   - Every private repository and every other namespace: [PROPRIETARY](templates/PROPRIETARY) as `LICENSE` (never an open-source license).
1. **Write root file**: set `<holder>` to `Médéric Hurier (Fmind)` in `fmind` (keep existing owner or ask in customer/employer repos) and `<year>` to `date +%Y`.
1. **Declare in `pyproject.toml`** (Python packages only): PEP 639 SPDX `license = "MIT"` or `license = "LicenseRef-Proprietary"` plus `license-files = ["LICENSE"]`.

## Gotchas

- **Namespace != content type**: `fmind` publishes both MIT code and CC-BY-4.0 courses; check content first.
- **Never create `LICENSE` beside `LICENSE.txt`**: two files create conflicting terms.
- **Valid SPDX only**: `"Proprietary"` fails PEP 639 build backends; always use `LicenseRef-Proprietary`.

## Documentation

- [Choose a License](https://choosealicense.com/) · [SPDX list](https://spdx.org/licenses/) · [PEP 639](https://peps.python.org/pep-0639/) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) ([legalcode.txt](https://creativecommons.org/licenses/by/4.0/legalcode.txt))
