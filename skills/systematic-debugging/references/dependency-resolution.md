# Dependency Resolution

Apply [systematic-debugging](../SKILL.md) to package resolver, lockfile, wheel, and build-backend failures.

1. **Reproduce with the same resolver**: distinguish direct constraints, transitive conflicts, platform markers, yanked releases, build-backend or wheel failures, authentication, network reachability, and stale locks.
1. **Route the fix**: inspect the lock and installed source without executing it and apply the smallest constraint fix only when authorized; route upgrades to [upgrade-tools](../../upgrade-tools/SKILL.md), registry facts to [research-brief](../../implementation-plan/references/research-brief.md), and CVE or license triage to [code-security](../../code-security/references/code-review/GUIDE.md).
