---
name: docker
description: "Run and inspect Docker containers, Compose services, and Colima on macOS."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/docker
  created: "2026-09-16"
  updated: "2026-09-16"
---

# Docker and Container Runtime Management

Use `docker`, `docker compose`, and `lazydocker` to manage container execution, services, and local debugging. [containerize](../containerize/SKILL.md) builds and signs images; [trivy](../security-review/references/trivy/GUIDE.md) scans them for vulnerabilities.

Docker, Compose, and Colima are host prerequisites; the tool extras do not install or start them. Inspect existing contexts before choosing a runtime. Container runs execute project code; obtain authority for untrusted images, network pulls, or consequential workloads. Preserve existing volumes and containers.

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
   docker info
   docker system df
   ```

1. **Manage Compose stacks**: start, inspect, and stop multi-container services with project isolation.

   ```bash
   docker compose up -d
   docker compose ps
   docker compose logs --tail 100 -f
   docker compose down
   ```

1. **Run interactive debugging**: use `lazydocker` for a terminal dashboard or attach to a container directly.

   ```bash
   lazydocker
   docker exec -it <container-id> sh
   ```

1. **Tail container logs boundedly**: inspect container output without flooding terminal buffers.

   ```bash
   docker logs --tail 100 <container-id>
   ```

1. **Clean up task containers**: always use `--rm` for ephemeral runs to avoid accumulating dead containers.

   ```bash
   docker run --rm -it <existing-image-or-approved-digest> echo "quick check"
   ```

## Gotchas

- **Colima socket path**: on macOS, Colima binds the Docker socket under `~/.colima/default/docker.sock`. If tools fail to locate the socket, set `DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"`.
- **VM memory limits**: containers in Colima run inside the VM; if a container exceeds the VM memory allocation, the Linux kernel terminates it with OOM (exit code 137). Adjust VM sizing with `colima start --memory <gb>`.
- **Volume mounts on macOS**: file system sharing between macOS and the Colima VM uses virtiofs; avoid heavy write-intensive build caches inside mounted macOS host directories.

## Documentation

- [Docker Documentation](https://docs.docker.com/) · [Docker Compose Reference](https://docs.docker.com/compose/)
- [Colima GitHub Repository](https://github.com/abiosoft/colima) · [Lazydocker](https://github.com/jesseduffield/lazydocker)
- Companion skills: [containerize](../containerize/SKILL.md) (image authoring), [trivy](../security-review/references/trivy/GUIDE.md) (scanning), [airflow](../airflow/SKILL.md) (local Airflow).
