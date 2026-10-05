---
name: project-license
description: "Choose, write, and declare a repository LICENSE (MIT, CC-BY-4.0, or proprietary) by namespace and content."
---

# Project License

Select, write, and declare the LICENSE a repository needs from its namespace, visibility, and content; [github-repository](../../../github-repository/SKILL.md) owns the remaining repository settings.

## Workflow

1. **Detect the namespace**: use `gh repo view --json nameWithOwner` for an existing GitHub repository; otherwise inspect project metadata and the agreed destination. Do not print raw Git remotes, which can contain embedded credentials.
1. **Read the existing license first**: `ls LICENSE*` and `gh repo view --json nameWithOwner,isPrivate,licenseInfo`; an existing license stays unless the user asked to replace it.
1. **Select the license**:
   - Public code under `fmind`, `fmind-ai`, or `mlops-courses`: MIT, from [MIT](templates/MIT).
   - Written course material (lessons, exercises, prose): CC-BY-4.0 as `LICENSE.txt`, fetched verbatim with `curl -fsSL https://creativecommons.org/licenses/by/4.0/legalcode.txt -o LICENSE.txt`; `mlops-courses/mlops-coding-course` is the reference example.
   - Every private repository and every other namespace: proprietary, from [PROPRIETARY](templates/PROPRIETARY); never an open-source license.
1. **Write the file** at the repository root:
   - Resolve `<holder>` from the namespace: `fmind` and `fmind-ai` use `Médéric Hurier (Fmind)`; `mlops-courses` uses `MLOps Courses`. When unsure, copy the holder from a sibling repository.
   - Resolve `<year>` to the current calendar year (`date +%Y`).
1. **Declare it in Python projects**: use the PEP 639 SPDX field `license = "MIT"` or `license = "LicenseRef-Proprietary"` plus `license-files = ["LICENSE"]` in `pyproject.toml`; content-only projects keep the license file without inventing a package manifest.

## Gotchas

- **Namespace is not content type**: `mlops-courses` holds both, MIT for code repositories and CC-BY-4.0 for the written course; inspect what the repository publishes before choosing.
- **Never duplicate `LICENSE.txt`**: a course repository may carry `LICENSE.txt`; writing `LICENSE` next to it leaves two conflicting licenses.
- **Use only SPDX expressions**: plain `"Proprietary"` is not a valid SPDX expression and modern build tools reject it; use `LicenseRef-Proprietary`.

## Documentation

- [Choose an Open Source License](https://choosealicense.com/) · [SPDX license list](https://spdx.org/licenses/) · [PEP 639](https://peps.python.org/pep-0639/)
- [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [legal code](https://creativecommons.org/licenses/by/4.0/legalcode.txt)
- Companion skills: [bootstrap](../bootstrap.md) (calls this guide when bootstrapping), [github-repository](../../../github-repository/SKILL.md) (repository settings).
