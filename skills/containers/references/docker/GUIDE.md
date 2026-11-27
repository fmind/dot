---
name: docker
description: "Run Docker, Compose, and Colima runtimes; sign and clean up container artifacts."
---

# Docker and Container Runtime Management

Manage local containers and Compose stacks with `docker` and `docker compose`. [containerize](../containerize/GUIDE.md) builds and signs Python images; [trivy](../../../code-security/references/trivy/GUIDE.md) scans them.

Never auto-start a daemon or VM, mutate the default context, or touch existing containers/volumes without scope: inspect `docker context ls`, pass `docker --context <context>` explicitly, and confirm authority before running untrusted images or consequential workloads.

## Runtime Selection

- **Linux**: host-installed Docker-compatible engine and Compose (outside user-space `mise`).
- **macOS**: Colima instead of Docker Desktop (`colima`, `lima`, `docker-cli`, `docker-compose`, `docker-buildx` in global macOS `mise`); see [colima](references/colima.md).

## Workflow

1. **Check daemon and disk headroom**: run `dot doctor --headroom` before large pulls or builds, then inspect daemon state:

   ```bash
   docker info --format 'Server={{.ServerVersion}} Driver={{.Driver}} Containers={{.Containers}} Images={{.Images}}'
   docker system df
   ```

1. **Operate Compose stacks**: pick a unique `-p <project>` for disposable stacks (`up --wait` fails on unhealthy services or 0-exit one-shot containers unless a dependent declares `condition: service_completed_successfully`, whereas `up -d` exits 0 once started):

   ```bash
   docker --context <context> compose -p <project> -f <compose-file> up --wait --wait-timeout 120
   docker --context <context> compose -p <project> -f <compose-file> ps
   docker --context <context> compose -p <project> -f <compose-file> logs --since 15m --tail 100 <service>
   docker --context <context> compose -p <project> -f <compose-file> down
   ```

1. **Clean up task artifacts**: run one-off containers with `docker run --rm <existing-image-or-approved-digest> <command>` and remove task-owned volumes, networks, images, and builders per [resource cleanup](references/resource-cleanup.md).

## Gotchas

- **Distro Buildx lags upstream**: Debian ships Buildx 0.13; check `docker buildx version` before passing newer flags like `--check`.
- **Exit 137 != guaranteed OOM**: inspect `.State.OOMKilled` and container/Colima VM memory limits before assuming OOM.

## References

- [colima](references/colima.md): Run Docker on macOS through Colima: VM start, socket, memory limits, and mounts.
- [cosign](references/cosign.md): Sign, verify, and attest image digests with keyless Sigstore.

## Documentation

- [Docker docs](https://docs.docker.com/) · [Compose](https://docs.docker.com/compose/) · [Engine releases](https://docs.docker.com/engine/release-notes/)
- Companion skills: [containerize](../containerize/GUIDE.md), [cloud-run](../../../gcloud/references/cloud-run/GUIDE.md), [trivy](../../../code-security/references/trivy/GUIDE.md), [orchestration-and-competitions](../../../mlops/references/orchestration-and-competitions.md).
