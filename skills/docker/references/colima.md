---
name: colima
description: "Run Docker on macOS through Colima: VM start, socket, memory limits, and mounts."
---

# Colima on macOS

Use [Colima](https://github.com/abiosoft/colima) (Lima-backed Linux VM) instead of Docker Desktop on macOS. `fmind/dot` installs `colima`, `lima`, `docker-cli`, `docker-compose`, and `docker-buildx` via macOS `mise` and wires mise shims into `~/.docker/config.json` `cliPluginsExtraDirs`. Pass `--activate=false` so the default Docker context stays untouched:

```bash
colima start --cpus 4 --memory 8 --activate=false
docker --context colima info --format '{{.ServerVersion}}'
colima status
colima stop
```

## Gotchas

- **Explicit socket fallback**: if a tool misses `~/.colima/default/docker.sock`, export `DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"`.
- **Verify OOM before resizing**: containers share the VM RAM cap; resize via `colima start --memory <gb>` only after confirming OOM.
- **Check VM mount driver**: `vz` uses `virtiofs` while QEMU profiles may use `sshfs` or `9p`; inspect `vmType` and `mountType` against [Colima defaults](https://github.com/abiosoft/colima/blob/main/embedded/defaults/colima.yaml) and keep write-heavy build caches inside the VM.

## Documentation

- [Colima](https://github.com/abiosoft/colima) · [releases](https://github.com/abiosoft/colima/releases)
