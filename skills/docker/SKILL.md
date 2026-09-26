---
name: docker
description: "Run and inspect Docker containers, Compose services, and Colima on macOS."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/docker
  created: "2026-09-16"
  updated: "2026-09-26"
---

# Docker and Container Runtime Management

Use `docker`, `docker compose`, and `lazydocker` to manage container execution, services, and local debugging. [containerize](../containerize/SKILL.md) builds and signs images; [trivy](../security-review/references/trivy/GUIDE.md) scans them for vulnerabilities.

Docker, Compose, and Colima are host prerequisites; workstation tools do not install or start them. Inspect `docker context ls` before choosing a runtime and pass `docker --context <context>` on consequential commands; do not change the persistent default just to run a task. Container runs execute project code; reuse authority for the requested workload and resolve missing scope before running untrusted images or consequential workloads. Preserve existing volumes and containers.

## Runtime Selection

- **macOS**: use [Colima](https://github.com/abiosoft/colima) as the default container runtime instead of Docker Desktop. Colima runs a lightweight Linux VM using Lima and provides a compatible Docker socket.
  ```bash
  colima start --cpu 4 --memory 8
  colima status
  colima stop
  ```
- **Linux**: use the existing Docker-compatible engine; host daemon installation is outside user-space mise setup.

## Workflow

1. **Verify daemon health and storage budget**: confirm the daemon is responsive and check storage footprint before launching workloads. Preserve 20 GiB free space on the workstation.

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

1. **Run interactive debugging**: use `lazydocker` for a terminal dashboard or attach to a container directly.

   ```bash
   lazydocker
   docker exec -it <container-id> sh
   ```

1. **Read container logs boundedly**: select the container and incident window; widen the window when needed, and keep streaming opt-in. Use `inspect --format` for specific state fields instead of dumping environment and mount details.

   ```bash
   docker logs --since 15m --tail 100 <container-id>
   ```

1. **Clean up task containers**: always use `--rm` for ephemeral runs to avoid accumulating dead containers.

   ```bash
   docker run --rm -it <existing-image-or-approved-digest> echo "quick check"
   ```

## Gotchas

- **Colima socket path**: on macOS, Colima binds the Docker socket under `~/.colima/default/docker.sock`. If tools fail to locate the socket, set `DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"`.
- **VM memory limits**: containers in Colima share the VM's memory budget. Exit code 137 means SIGKILL and does not alone prove an OOM; check the container's `State.OOMKilled`, configured limits, and runtime/kernel evidence before changing `colima start --memory <gb>`.
- **Volume mounts on macOS**: the driver depends on the VM profile: `vz` supports virtiofs, while QEMU profiles can use sshfs or 9p. Inspect the profile's `vmType` and `mountType` against [Colima's configuration](https://github.com/abiosoft/colima/blob/main/embedded/defaults/colima.yaml) before diagnosing performance; keep write-heavy build caches inside the VM when practical.

## Documentation

- [Docker Documentation](https://docs.docker.com/) · [Docker Compose Reference](https://docs.docker.com/compose/)
- [Colima GitHub Repository](https://github.com/abiosoft/colima) · [Lazydocker](https://github.com/jesseduffield/lazydocker)
- Releases: [Docker Engine](https://docs.docker.com/engine/release-notes/) · [Colima](https://github.com/abiosoft/colima/releases)
- Companion skills: [containerize](../containerize/SKILL.md) (image authoring), [trivy](../security-review/references/trivy/GUIDE.md) (scanning), [airflow](../airflow/SKILL.md) (local Airflow).
