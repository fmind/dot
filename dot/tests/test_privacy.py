from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from fmind_dot.cli import app
from fmind_dot.privacy import PRIVACY_SCHEMA
from tests.fakes import CliRunner


def test_privacy_cli_clean_and_quiet_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "notes.md").write_text("Contact contact@fmind.dev or alice@example.com\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, timeout=30)
    monkeypatch.chdir(repo)

    res = CliRunner().invoke(app, ["privacy"])
    assert res.exit_code == 0, res.stderr
    assert "✓ " in res.stdout
    assert "no privacy findings" in res.stdout

    quiet = CliRunner().invoke(app, ["privacy", "--quiet"])
    assert quiet.exit_code == 0
    assert quiet.stdout == ""

    as_json = CliRunner().invoke(app, ["privacy", "--json", str(repo)])
    assert as_json.exit_code == 0
    payload = json.loads(as_json.stdout)
    assert payload["schema"] == PRIVACY_SCHEMA
    assert payload["passed"] is True
    assert len(payload["targets"]) == 1
    assert payload["targets"][0]["path"] == str(repo.resolve())
    assert payload["targets"][0]["findings"] == []

    quiet_json = CliRunner().invoke(app, ["privacy", "--json", "-q", str(repo)])
    assert quiet_json.exit_code == 0
    assert json.loads(quiet_json.stdout) == {"schema": PRIVACY_SCHEMA, "passed": True, "targets": []}


def test_privacy_cli_reports_findings_and_missing_dir(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    bad_email = "@".join(("alice", "internal-corp.io"))
    (repo / "leak.txt").write_text(f"email = {bad_email}\n", encoding="utf-8")
    missing = tmp_path / "missing"

    res = CliRunner().invoke(app, ["privacy", str(repo), str(missing)])
    assert res.exit_code == 1
    assert "✗ " in res.stdout
    assert "unapproved email domain 'internal-corp.io'" in res.stdout
    assert "directory not found" in res.stdout

    as_json = CliRunner().invoke(app, ["privacy", "--json", str(repo), str(missing)])
    assert as_json.exit_code == 1
    payload = json.loads(as_json.stdout)
    assert payload["schema"] == PRIVACY_SCHEMA
    assert payload["passed"] is False
    assert len(payload["targets"]) == 2
    assert not payload["targets"][0]["passed"]
    assert not payload["targets"][1]["passed"]


def test_privacy_cli_skips_generated_lockfiles(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    maint = "@".join(("maintainer", "thirdparty.io"))
    dev = "@".join(("dev", "thirdparty.io"))
    (repo / "uv.lock").write_text(f'email = "{maint}"\n', encoding="utf-8")
    (repo / ".mise/locks/npm-tool").mkdir(parents=True)
    (repo / ".mise/locks/npm-tool/aube-lock.yaml").write_text(f"author: {dev}\n", encoding="utf-8")

    res = CliRunner().invoke(app, ["privacy", str(repo)])
    assert res.exit_code == 0, res.stdout + res.stderr


def test_privacy_cli_honors_config_flag_and_fails_closed_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("DOT_CONFIG_PATH", raising=False)

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "notes.md").write_text("Owned by secret-client-42\n", encoding="utf-8")

    cfg = tmp_path / "client.yaml"
    cfg.write_text("trust:\n  github_owners: [secret-client-42]\n", encoding="utf-8")

    flagged = CliRunner().invoke(app, ["-c", str(cfg), "privacy", "--json", str(repo)])
    assert flagged.exit_code == 1
    payload = json.loads(flagged.stdout)
    assert payload["passed"] is False
    assert any("secret-client-42" in item for item in payload["targets"][0]["findings"])

    missing_cfg = tmp_path / "does-not-exist.yaml"
    missing = CliRunner().invoke(app, ["--config", str(missing_cfg), "privacy", "--json", str(repo)])
    assert missing.exit_code == 1
    missing_payload = json.loads(missing.stdout)
    assert missing_payload["passed"] is False
    assert any("file not found" in item for item in missing_payload["targets"][0]["findings"])

    bad_home_cfg = CliRunner().invoke(app, ["-c", "~no_such_user_xyz_99/dot.yaml", "privacy", "--json", str(repo)])
    assert bad_home_cfg.exit_code == 1
    bad_home_payload = json.loads(bad_home_cfg.stdout)
    assert bad_home_payload["passed"] is False
    assert any("invalid home prefix" in item for item in bad_home_payload["targets"][0]["findings"])


def test_privacy_git_subdir_nested_git_errors_and_unreadable_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    home = tmp_path / "home"
    (home / ".config/git").mkdir(parents=True)
    bad_gitconfig_email = "@".join(("owner", "employer-priv.net"))
    (home / ".gitconfig").write_text(f'[user]\n\temail = {bad_gitconfig_email}\n\tuser = "quoted-handle"\n')
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("DOT_CONFIG_PATH", raising=False)

    repo = tmp_path / "repo"
    sub = repo / "pkg"
    (sub / ".venv").mkdir(parents=True)
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, timeout=30)
    (repo / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    (sub / ".venv/pkg.txt").write_text("email = " + "@".join(("x", "thirdparty.io")) + "\n", encoding="utf-8")
    (sub / "ok.py").write_text('OK = "alice@example.com"\n', encoding="utf-8")

    # Subdirectory of a Git repo respects .gitignore.
    sub_ok = CliRunner().invoke(app, ["privacy", "--json", str(sub)])
    assert sub_ok.exit_code == 0, sub_ok.stdout + sub_ok.stderr

    # ~/.gitconfig email and quoted user token are detected.
    (sub / "leak.txt").write_text("Using employer-priv and quoted-handle\n", encoding="utf-8")
    sub_leak = CliRunner().invoke(app, ["privacy", "--json", str(sub)])
    assert sub_leak.exit_code == 1
    findings = json.loads(sub_leak.stdout)["targets"][0]["findings"]
    assert any("employer-priv" in f or "quoted-handle" in f for f in findings)
    (sub / "leak.txt").unlink()

    # Non-git parent prunes nested .git/ and still flags symlinked .age files.
    parent = tmp_path / "non-git-parent"
    (parent / "nested/.git").mkdir(parents=True)
    (parent / "nested/.git/config").write_text("email = " + "@".join(("x", "internal-git.io")) + "\n")
    valid_age = parent / "valid.age"
    valid_age.write_bytes(b"-----BEGIN AGE ENCRYPTED FILE-----\nabc\n")
    (parent / "link.age").symlink_to(valid_age)
    non_git = CliRunner().invoke(app, ["privacy", "--json", str(parent)])
    assert non_git.exit_code == 1
    non_git_findings = json.loads(non_git.stdout)["targets"][0]["findings"]
    assert non_git_findings == ["link.age: encrypted .age source must not be a symlink"]

    # Corrupt .git and dangling .git symlink fail closed (at root and in subdirectories) without a traceback.
    corrupt = tmp_path / "corrupt"
    corrupt_sub = corrupt / "pkg"
    corrupt_sub.mkdir(parents=True)
    (corrupt / ".git").write_text("gitdir: /nonexistent/gitdir\n", encoding="utf-8")
    for target in (corrupt, corrupt_sub):
        corrupt_res = CliRunner().invoke(app, ["privacy", "--json", str(target)])
        assert corrupt_res.exit_code == 1
        corrupt_payload = json.loads(corrupt_res.stdout)
        assert corrupt_payload["passed"] is False
        assert any("git rev-parse failed" in f for f in corrupt_payload["targets"][0]["findings"])

    dangling = tmp_path / "dangling-git"
    dangling_sub = dangling / "pkg"
    dangling_sub.mkdir(parents=True)
    (dangling / ".git").symlink_to(tmp_path / "missing-gitdir")
    for target in (dangling, dangling_sub):
        dangling_res = CliRunner().invoke(app, ["privacy", "--json", str(target)])
        assert dangling_res.exit_code == 1
        assert any("git rev-parse failed" in f for f in json.loads(dangling_res.stdout)["targets"][0]["findings"])

    # Corrupt branch ref (loose or packed) or detached invalid HEAD fails closed instead of pretending unborn.
    broken_head = tmp_path / "broken-head"
    broken_head.mkdir()
    subprocess.run(["git", "-C", str(broken_head), "init", "-q"], check=True, timeout=30)
    (broken_head / ".git/HEAD").write_text("0" * 40 + "\n", encoding="utf-8")
    broken_res = CliRunner().invoke(app, ["privacy", "--json", str(broken_head)])
    assert broken_res.exit_code == 1
    assert any("git rev-parse HEAD failed" in f for f in json.loads(broken_res.stdout)["targets"][0]["findings"])

    corrupt_ref = tmp_path / "corrupt-ref"
    corrupt_ref.mkdir()
    subprocess.run(["git", "-C", str(corrupt_ref), "init", "-q", "-b", "main"], check=True, timeout=30)
    (corrupt_ref / ".git/refs/heads/main").write_text("not-a-sha\n", encoding="utf-8")
    corrupt_ref_res = CliRunner().invoke(app, ["privacy", "--json", str(corrupt_ref)])
    assert corrupt_ref_res.exit_code == 1
    assert any("git rev-parse HEAD failed" in f for f in json.loads(corrupt_ref_res.stdout)["targets"][0]["findings"])

    packed_corrupt = tmp_path / "packed-corrupt"
    packed_corrupt.mkdir()
    subprocess.run(["git", "-C", str(packed_corrupt), "init", "-q", "-b", "main"], check=True, timeout=30)
    (packed_corrupt / ".git/packed-refs").write_text(
        f"# pack-refs with: peeled fully-peeled sorted\n{'1' * 40} refs/heads/main\n", encoding="utf-8"
    )
    packed_res = CliRunner().invoke(app, ["privacy", "--json", str(packed_corrupt)])
    assert packed_res.exit_code == 1
    assert any("git rev-parse HEAD failed" in f for f in json.loads(packed_res.stdout)["targets"][0]["findings"])

    # Broken global gitconfig fails closed on a plain directory instead of silently skipping git detection.
    bad_cfg = tmp_path / "bad-gitconfig"
    bad_cfg.write_text("[broken\n", encoding="utf-8")
    plain_dir = tmp_path / "plain-for-bad-cfg"
    plain_dir.mkdir()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(bad_cfg))
    bad_cfg_res = CliRunner().invoke(app, ["privacy", "--json", str(plain_dir)])
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)
    assert bad_cfg_res.exit_code == 1
    assert any("git rev-parse failed" in f for f in json.loads(bad_cfg_res.stdout)["targets"][0]["findings"])

    # Non-regular .age path (FIFO) fails closed without blocking on open().
    fifo_dir = tmp_path / "fifo-age"
    fifo_dir.mkdir()
    os.mkfifo(fifo_dir / "pipe.age")
    fifo_res = CliRunner().invoke(app, ["privacy", "--json", str(fifo_dir)])
    assert fifo_res.exit_code == 1
    assert any("must be a regular file" in f for f in json.loads(fifo_res.stdout)["targets"][0]["findings"])

    # Unreadable regular file fails closed instead of being silently skipped.
    if os.geteuid() != 0:
        unreadable = sub / "secret.txt"
        unreadable.write_text("ok\n", encoding="utf-8")
        unreadable.chmod(0o000)
        try:
            unreadable_res = CliRunner().invoke(app, ["privacy", "--json", str(sub)])
            assert unreadable_res.exit_code == 1
            assert any(
                "secret.txt: unreadable file" in f for f in json.loads(unreadable_res.stdout)["targets"][0]["findings"]
            )
        finally:
            unreadable.chmod(0o600)
            unreadable.unlink()


def test_privacy_staged_scans_index_blobs_and_rejects_non_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("DOT_CONFIG_PATH", raising=False)

    non_git = tmp_path / "plain"
    non_git.mkdir()
    non_git_res = CliRunner().invoke(app, ["privacy", "--staged", "--json", str(non_git)])
    assert non_git_res.exit_code == 1
    assert any(
        "--staged requires a Git repository" in f for f in json.loads(non_git_res.stdout)["targets"][0]["findings"]
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, timeout=30)
    bad_email = "@".join(("alice", "staged-leak.io"))
    sample = repo / "notes.md"
    # Stage a leak, then fix only the working tree: --staged must still catch the staged blob.
    sample.write_text(f"Contact {bad_email}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "notes.md"], check=True, timeout=30)
    sample.write_text("Contact alice@example.com\n", encoding="utf-8")

    staged_leak = CliRunner().invoke(app, ["privacy", "--staged", "--json", str(repo)])
    assert staged_leak.exit_code == 1
    assert any("staged-leak.io" in f for f in json.loads(staged_leak.stdout)["targets"][0]["findings"])

    # Stage the clean version, then add an unstaged leak: --staged must pass.
    subprocess.run(["git", "-C", str(repo), "add", "notes.md"], check=True, timeout=30)
    sample.write_text(f"Unstaged {bad_email}\n", encoding="utf-8")
    (repo / "binary.bin").write_bytes(b"\x00\x01" + bad_email.encode("utf-8"))
    subprocess.run(["git", "-C", str(repo), "add", "binary.bin"], check=True, timeout=30)
    staged_clean = CliRunner().invoke(app, ["privacy", "--staged", "--json", str(repo)])
    assert staged_clean.exit_code == 0, staged_clean.stdout + staged_clean.stderr

    # Staged plaintext .age and symlinked .age are both rejected.
    valid_age = repo / "valid.age"
    valid_age.write_bytes(b"-----BEGIN AGE ENCRYPTED FILE-----\nabc\n")
    plain_age = repo / "plain.age"
    plain_age.write_text("SECRET=plain\n", encoding="utf-8")
    link_age = repo / "link.age"
    link_age.symlink_to(valid_age)
    subprocess.run(["git", "-C", str(repo), "add", "valid.age", "plain.age", "link.age"], check=True, timeout=30)
    age_res = CliRunner().invoke(app, ["privacy", "--staged", "--json", str(repo)])
    assert age_res.exit_code == 1
    age_findings = json.loads(age_res.stdout)["targets"][0]["findings"]
    assert any("plain.age: .age source is not age-encrypted ciphertext" in f for f in age_findings)
    assert any("link.age: encrypted .age source must not be a symlink" in f for f in age_findings)
    assert not any("valid.age" in f for f in age_findings)

    # CRLF-corrupted .age blob is rejected (raw bytes, no universal-newline coercion),
    # while non-UTF-8 binary blobs without NUL bytes are skipped cleanly.
    subprocess.run(
        ["git", "-C", str(repo), "rm", "-q", "-f", "--cached", "plain.age", "link.age"], check=True, timeout=30
    )
    (repo / "crlf.age").write_bytes(b"age-encryption.org/v1\r\nbody\n")
    (repo / "raw.dat").write_bytes(b"\xff\xfe" + bad_email.encode("utf-8"))
    subprocess.run(["git", "-C", str(repo), "add", "crlf.age", "raw.dat"], check=True, timeout=30)
    crlf_res = CliRunner().invoke(app, ["privacy", "--staged", "--json", str(repo)])
    assert crlf_res.exit_code == 1
    assert json.loads(crlf_res.stdout)["targets"][0]["findings"] == [
        "crlf.age: .age source is not age-encrypted ciphertext"
    ]

    # Post-commit typechanges (T): symlink->file leak and regular .age->symlink must both be caught.
    subprocess.run(
        ["git", "-C", str(repo), "rm", "-q", "-f", "--cached", "crlf.age", "raw.dat", "binary.bin"],
        check=True,
        timeout=30,
    )
    (repo / "target.txt").write_text("clean\n", encoding="utf-8")
    (repo / "swap.txt").symlink_to("target.txt")
    subprocess.run(["git", "-C", str(repo), "add", "target.txt", "swap.txt", "valid.age"], check=True, timeout=30)
    git_env = {
        "GIT_AUTHOR_NAME": "Fmind",
        "GIT_AUTHOR_EMAIL": "dev@fmind.dev",
        "GIT_COMMITTER_NAME": "Fmind",
        "GIT_COMMITTER_EMAIL": "dev@fmind.dev",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
    }
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], env=git_env, check=True, timeout=30)
    (repo / "swap.txt").unlink()
    (repo / "swap.txt").write_text(f"Leaked {bad_email}\n", encoding="utf-8")
    (repo / "valid.age").unlink()
    (repo / "valid.age").symlink_to("target.txt")
    subprocess.run(["git", "-C", str(repo), "add", "swap.txt", "valid.age"], check=True, timeout=30)
    typechange_res = CliRunner().invoke(app, ["privacy", "--staged", "--json", str(repo)])
    assert typechange_res.exit_code == 1
    tc_findings = json.loads(typechange_res.stdout)["targets"][0]["findings"]
    assert any("swap.txt: unapproved email domain 'staged-leak.io'" in f for f in tc_findings)
    assert any("valid.age: encrypted .age source must not be a symlink" in f for f in tc_findings)

    # Subdirectory staged scan respects root-relative lockfile skips via --relative.
    sub = repo / "sub"
    sub.mkdir()
    (sub / "uv.lock").write_text(f'email = "{bad_email}"\n', encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "sub/uv.lock"], check=True, timeout=30)
    sub_res = CliRunner().invoke(app, ["privacy", "--staged", "--json", str(sub)])
    assert sub_res.exit_code == 0, sub_res.stdout + sub_res.stderr
