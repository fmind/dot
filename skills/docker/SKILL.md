---
name: docker
description: "Run Docker, Compose, and Colima; build, scan, sign, and verify Python images."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/docker
  created: "2026-09-16"
  updated: "2026-11-07"
---

# Docker and Container Runtime Management

Use `docker`, `docker compose`, and `lazydocker` to manage container execution, services, and local debugging. The [containerize](references/containerize/GUIDE.md) guide builds, publishes, and signs Python images; [trivy](../code-security/references/trivy/GUIDE.md) scans them for vulnerabilities.

On Linux, Docker and Compose are host prerequisites. On macOS, the global mise config installs Colima, Lima, and the Docker CLI with Compose and Buildx ([Colima](references/colima.md)). Nothing here starts a daemon or VM. Inspect `docker context ls` before choosing a runtime and pass `docker --context <context>` on consequential commands; do not change the persistent default just to run a task. Container runs execute project code; reuse authority for the requested workload and resolve missing scope before running untrusted images or consequential workloads. Preserve existing volumes and containers.

## Runtime Selection

- **Linux**: use the existing Docker-compatible engine; host daemon installation is outside user-space mise setup.
- **macOS**: use Colima instead of Docker Desktop; read [colima](references/colima.md) for its context, socket, memory, and mount behavior.

## Workflow

1. **Verify daemon health and storage budget**: confirm the daemon is responsive and check storage footprint before launching workloads. Run `dot doctor --headroom` before large pulls or builds.

   ```bash
   docker info --format 'Server={{.ServerVersion}} Driver={{.Driver}} Containers={{.Containers}} Images={{.Images}}'
   docker system df
   ```

1. **Manage Compose stacks**: resolve the Compose file and project name first. Use a unique name for a new disposable stack; reuse an existing project's name only when operating that stack is in scope. `up --wait` exits non-zero when a service fails to start or stays unhealthy, while `up -d` succeeds once containers start; a one-shot service that exits 0 also fails `--wait` unless another service depends on it with `condition: service_completed_successfully`.

   ```bash
   docker --context <context> compose -p <project> -f <compose-file> up --wait --wait-timeout 120
   docker --context <context> compose -p <project> -f <compose-file> ps
   docker --context <context> compose -p <project> -f <compose-file> logs --since 15m --tail 100 <service>
   docker --context <context> compose -p <project> -f <compose-file> down
   ```

1. **Clean up task resources**: use `docker run --rm <existing-image-or-approved-digest> <command>` for ephemeral runs, and follow [resource cleanup](references/resource-cleanup.md) for task-created volumes, networks, images, and builders.

## Gotchas

- **The Linux engine comes from the distro**: Docker and Buildx can lag upstream (Debian ships Buildx 0.13), so check `docker buildx version` before using a newer build flag such as `--check`.
- **Exit 137 is SIGKILL, not proof of OOM**: check `.State.OOMKilled` and the memory limit first; on macOS, Colima's VM budget also applies.

## Task guides

<!-- guides:start -->

- [colima](references/colima.md): Run Docker on macOS through Colima: VM start, socket, memory limits, and mounts.
- [containerize](references/containerize/GUIDE.md): Build, scan, sign, and verify Python container images with Trivy and Cosign.
- [cosign](references/cosign.md): Sign, verify, and attest image digests with keyless Sigstore.

<!-- guides:end -->

## Documentation

- [Docker Documentation](https://docs.docker.com/) · [Docker Compose Reference](https://docs.docker.com/compose/)
- [Lazydocker](https://github.com/jesseduffield/lazydocker)
- Releases: [Docker Engine](https://docs.docker.com/engine/release-notes/)
- Companion skills: [cloud-run](../cloud-run/SKILL.md) (deployment), [trivy](../code-security/references/trivy/GUIDE.md) (scanning), [airflow](../airflow/SKILL.md) (local Airflow).
