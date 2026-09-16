# Docker Resource Cleanup

Clean up the disposable resources created by this task, including after a failed smoke test. A stopped resource is not evidence that it is disposable. Check the Docker context before both creation and deletion; a remote daemon's storage is not the workstation's storage.

1. Record the baseline with `docker system df`, `docker ps -a`, and `docker buildx ls`. Use a unique task label/name and record exact container, volume, network, image and builder identifiers as they are created. Mark persistent data and requested outputs explicitly.
1. Prefer `docker run --rm` for short tests. Arrange teardown in the test fixture or `finally` block so assertion failures still stop and remove the exact test container. Preserve its exit status and bounded diagnostic output before teardown.
1. For an exclusively task-created Compose project, use the same files and unique project name for `docker compose -p <task-project> -f <compose-file> down`. Use `--volumes` only when every affected volume was created for this task and contains disposable test data. Do not add `--remove-orphans` or `--rmi all` as generic cleanup defaults.
1. Remove remaining task-created disposable volumes and networks by recorded ID/name after their consumers stop. Reinspect ownership and use before deletion. Preserve pre-existing resources, bind-mounted source/data, databases, and resources another task has adopted; uncertainty means retain and report.
1. Remove only temporary image tags created by this task with `docker image rm <task-tag>`, without force, after confirming no consumer needs them. Preserve shared base images and final image deliverables. A shared layer may remain: tag removal does not guarantee that all reported image bytes become free.
1. Remove an exclusively task-created temporary builder by name with `docker buildx rm <task-builder>` once idle; do not retain its state unless it is an intentional reusable artifact. For a shared builder, inspect `docker buildx du --builder <builder>` and use its reviewed garbage-collection policy. Broad `docker system prune`, volume prune and builder prune do not belong in automatic task teardown.
1. Delete task-created temporary archives such as `tmp/image.tar` after the final consumer completes unless delivery requires them. Account for temporary contexts, scan outputs and test data too. Recheck `docker system df` and filesystem free space; report retained resources and reasons without claiming concurrent disk changes as your own savings.

For a persistent local builder on a 100 GiB workstation, propose a 5 GiB build-cache budget and a 20 GiB free-space reserve. Inspect the driver and existing policy first: daemon and standalone BuildKit settings differ, garbage collection is not a hard disk quota, and cache limits do not bound images, volumes or writable container layers. Do not change a shared daemon or builder policy as an incidental build step.

## Documentation

- [Compose down](https://docs.docker.com/reference/cli/docker/compose/down/) · [Remove a builder](https://docs.docker.com/reference/cli/docker/buildx/rm/) · [Build cache garbage collection](https://docs.docker.com/build/cache/garbage-collection/)
