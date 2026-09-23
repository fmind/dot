"""The distributable archives retain the project's license notice."""

import os
import subprocess
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_built_distributions_include_the_canonical_license(tmp_path: Path) -> None:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("UV_")}
    result = subprocess.run(
        ["uv", "build", "--no-config", "--project", str(ROOT / "dot"), "--out-dir", str(tmp_path)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    expected = (ROOT / "LICENSE").read_bytes()
    with zipfile.ZipFile(next(tmp_path.glob("*.whl"))) as wheel:
        metadata_path = next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = Parser().parsestr(wheel.read(metadata_path).decode())
        assert metadata["License-Expression"] == "MIT"
        assert metadata.get_all("License-File") == ["LICENSE"]
        assert wheel.read(metadata_path.removesuffix("METADATA") + "licenses/LICENSE") == expected
    with tarfile.open(next(tmp_path.glob("*.tar.gz"))) as source:
        license_path = next((name for name in source.getnames() if name.endswith("/LICENSE")), None)
        assert license_path is not None
        stream = source.extractfile(license_path)
        assert stream is not None
        assert stream.read() == expected
