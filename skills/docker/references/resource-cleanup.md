# Docker Resource Cleanup

Clean up only the Docker resources this task recorded as it created them, on success and failure, in the same Docker context that created them.

- **Keep a free-space floor**: keep at least 20 GiB free during a build (the `dot doctor --headroom` warning level; it fails below 10 GiB) and propose a 5 GiB cache budget for a persistent local builder. Never change a shared daemon or builder policy as an incidental build step.
- **Compose teardown stays narrow**: `docker compose -p <task-project> -f <file> down`; add `--volumes` only when every volume is task-created test data, and never add `--remove-orphans` or `--rmi all` by default.
- **Remove by recorded name or ID**: volumes, networks, temporary image tags (`docker image rm` without force), builders (`docker buildx rm <task-builder>`), and archives such as `tmp/image.tar`; when ownership is uncertain, retain and report.
- **Never prune in teardown**: `docker system prune`, volume prune, and builder prune do not belong in automatic cleanup; reuse a shared builder cache under its budget instead.
- **Report what remains**: recheck `docker system df` and free space, and never count concurrent disk changes as your own savings.

## Documentation

- [Compose down](https://docs.docker.com/reference/cli/docker/compose/down/) · [Remove a builder](https://docs.docker.com/reference/cli/docker/buildx/rm/) · [Build cache garbage collection](https://docs.docker.com/build/cache/garbage-collection/)
