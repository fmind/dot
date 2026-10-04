---
name: docker
description: "Run and inspect Docker containers, Compose stacks, and Colima."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/docker
  created: "2026-09-16"
  updated: "2026-10-04"
---

# Docker and Container Runtime Management

Use `docker`, `docker compose`, and `lazydocker` to manage container execution, services, and local debugging. [containerize](../containerize/SKILL.md) builds and signs images; [trivy](../code-security/references/trivy/GUIDE.md) scans them for vulnerabilities.

Docker, Compose, and Colima are host prerequisites; workstation tools do not install or start them. Inspect `docker context ls` before choosing a runtime and pass `docker --context <context>` on consequential commands; do not change the persistent default just to run a task. Container runs execute project code; reuse authority for the requested workload and resolve missing scope before running untrusted images or consequential workloads. Preserve existing volumes and containers.

## Runtime Selection

- **Linux**: use the existing Docker-compatible engine; host daemon installation is outside user-space mise setup.
- **macOS**: use Colima instead of Docker Desktop; read [colima](references/colima.md) for its context, socket, memory, and mount behavior.

## Workflow

1. **Verify daemon health and storage budget**: confirm the daemon is responsive and check storage footprint before launching workloads. Run `dot doctor --headroom` before large pulls or builds.

   ```bash
   docker info --format 'Server={{.ServerVersion}} Driver={{.Driver}} Containers={{.Containers}} Images={{.Images}}'
   docker system df
   ```

1. **Manage Compose stacks**: resolve the Compose file and project name first. Use a unique name for a new disposable stack; reuse an existing project's name only when operating that stack is in scope.

   ```bash
   docker --context <context> compose -p <project> -f <compose-file> up -d
   docker --context <context> compose -p <project> -f <compose-file> ps
   docker --context <context> compose -p <project> -f <compose-file> logs --since 15m --tail 100 <service>
   docker --context <context> compose -p <project> -f <compose-file> down
   ```

1. **Leave interactive debugging to the user**: `lazydocker` and `docker exec -it <container-id> sh` need a TTY; suggest them for user-driven sessions and use bounded non-interactive `docker exec <container-id> <command>` otherwise.

1. **Read container logs boundedly**: select the container and incident window; widen the window when needed, and keep streaming opt-in. Use `inspect --format` for specific state fields instead of dumping environment and mount details.

   ```bash
   docker logs --since 15m --tail 100 <container-id>
   ```

1. **Clean up task resources**: use `docker run --rm <existing-image-or-approved-digest> <command>` for ephemeral runs, and follow [resource cleanup](../containerize/references/resource-cleanup.md) for task-created volumes, networks, images, and builders.

## Gotchas

- **Exit 137 is not proof of OOM**: it means SIGKILL; check `docker inspect --format '{{.State.OOMKilled}}' <container-id>`, the configured memory limit, and kernel/runtime evidence before changing limits. On macOS, Colima's VM budget also applies; see [colima](references/colima.md).

## Task guides

<!-- guides:start -->

- [colima](references/colima.md): Run Docker on macOS through Colima: VM start, socket, memory limits, and mounts.

<!-- guides:end -->

## Documentation

- [Docker Documentation](https://docs.docker.com/) · [Docker Compose Reference](https://docs.docker.com/compose/)
- [Lazydocker](https://github.com/jesseduffield/lazydocker)
- Releases: [Docker Engine](https://docs.docker.com/engine/release-notes/)
- Companion skills: [containerize](../containerize/SKILL.md) (image authoring), [trivy](../code-security/references/trivy/GUIDE.md) (scanning), [airflow](../airflow/SKILL.md) (local Airflow).
