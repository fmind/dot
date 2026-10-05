---
name: colima
description: "Run Docker on macOS through Colima: VM start, socket, memory limits, and mounts."
---

# Colima on macOS

Use [Colima](https://github.com/abiosoft/colima) as the default macOS container runtime instead of Docker Desktop. Colima runs a lightweight Linux VM using Lima and provides a compatible Docker socket. `--activate=false` keeps the current Docker context; address the VM explicitly.

```bash
colima start --cpus 4 --memory 8 --activate=false
docker --context colima info --format '{{.ServerVersion}}'
colima status
colima stop
```

## Gotchas

- **Set `DOCKER_HOST` if the socket is missing**: Colima binds the Docker socket under `~/.colima/default/docker.sock`. If tools fail to locate the socket, set `DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"`.
- **Confirm OOM before resizing VM memory**: containers share the VM's memory budget; after confirming a real OOM, adjust it with `colima start --memory <gb>`.
- **Mount drivers depend on the VM profile**: `vz` supports virtiofs, while QEMU profiles can use sshfs or 9p. Inspect the profile's `vmType` and `mountType` against [Colima's configuration](https://github.com/abiosoft/colima/blob/main/embedded/defaults/colima.yaml) before diagnosing performance; keep write-heavy build caches inside the VM when practical.

## Documentation

- [Colima GitHub Repository](https://github.com/abiosoft/colima)
- Releases: [Colima](https://github.com/abiosoft/colima/releases)
