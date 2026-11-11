# Verify Release Assets

Download assets into a fresh temp directory and verify the checksum manifest, immutable release attestations, and build provenance:

```bash
release_dir=$(mktemp -d)
gh release download "$tag" -R "$repo" --dir "$release_dir"
gh release verify "$tag" -R "$repo"
gh release verify-asset "$tag" "$release_dir/checksums.txt" -R "$repo"
(cd "$release_dir" && shasum -a 256 -c checksums.txt)
asset=project_vX.Y.Z_linux_amd64.tar.gz
signer_workflow="$repo/.github/workflows/release.yml"
gh release verify-asset "$tag" "$release_dir/$asset" -R "$repo"
gh attestation verify "$release_dir/$asset" --repo "$repo" --signer-workflow "$signer_workflow" --source-ref "refs/tags/$tag" --source-digest "$release_sha"
```

- **Immutable releases required**: `gh release verify` and `verify-asset` work only on immutable releases (auto-generated source tarballs are excluded).
- **Verify `checksums.txt` before its entries**, and run `gh attestation verify` with `--signer-workflow` wherever build provenance is emitted.
- **Fail closed**: missing assets, checksums, or attestations fail verification — never regenerate or replace published artifacts.
