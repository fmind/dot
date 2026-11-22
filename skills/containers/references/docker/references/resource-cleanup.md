# Docker Resource Cleanup

Remove only resources recorded as created by this task, in the originating Docker context, on both success and failure:

- **Respect disk floors**: keep ≥20 GiB free during builds (`dot doctor --headroom` warns <20 GiB and fails <10 GiB; propose a 5 GiB GC cap for persistent local builders without altering shared daemon policies unasked).
- **Keep Compose teardown narrow**: run `docker compose -p <task-project> -f <file> down` (add `--volumes` only for disposable test volumes; never pass `--remove-orphans` or `--rmi all` by default).
- **Delete by exact recorded name/ID**: volumes, networks, temp tags (`docker image rm` without `-f`), `docker buildx rm <task-builder>`, and `tmp/image.tar` (keep and report anything with uncertain ownership).
- **Never run global prunes in teardown**: skip `docker system/volume/builder prune`; recheck `docker system df` and free bytes without attributing concurrent changes to your cleanup.

## Documentation

- [Compose down](https://docs.docker.com/reference/cli/docker/compose/down/) · [buildx rm](https://docs.docker.com/reference/cli/docker/buildx/rm/) · [Build cache GC](https://docs.docker.com/build/cache/garbage-collection/)
