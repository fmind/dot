# FKF URI Examples

The grammar is `<path>[?jq=<expr>][#<fragment>]`, a base-defined lowercase entity scheme, or external HTTPS. Directories end in `/`.

| Form              | Example                                                                            |
| ----------------- | ---------------------------------------------------------------------------------- |
| Event date        | `events/2026-05-04/`                                                               |
| Event document    | `events/2026-05-04/github-pull-requests.json`                                      |
| Event record      | `events/2026-05-04/github-pull-requests.json#https://github.com/fmind/fkf/pull/42` |
| Index document    | `index/github-repositories.json`                                                   |
| Index record      | `index/github-repositories.json#fmind/fkf`                                         |
| Task heading      | `tasks/2026-08-22/review/TASKS.md#verification`                                    |
| Project heading   | `projects/fkf.md#decisions`                                                        |
| Wiki heading      | `wiki/retrieval-boundary.md#decision`                                              |
| Graph edge caches | `graph.tsv`, `graph.dst.tsv`, `graph.offsets.tsv`                                  |
| Configuration     | `fkf.yaml`                                                                         |
| Base instructions | `AGENTS.md`                                                                        |
| Person entity     | `person:email/marc@example.test`                                                   |
| Repository entity | `repo:github.com/fmind/fkf`                                                        |
| External page     | `https://github.com/fmind/fkf/pull/42`                                             |

Fragments must exist. `?jq=` is in-process, bounded, and has no environment, filesystem, network, input, or import access. Entity and HTTPS reads return only local graph neighbours; they never fetch the URL.
