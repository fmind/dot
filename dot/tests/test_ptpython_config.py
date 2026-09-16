"""Exercise configuration loading with ptpython's empty exec namespace."""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest

CONFIG = Path(__file__).resolve().parents[2] / "dot_config/ptpython/config.py"


@pytest.mark.parametrize("with_theme", [False, True])
def test_config_without_module_globals(tmp_path: Path, monkeypatch, with_theme: bool):
    config = tmp_path / "config.py"
    config.write_bytes(CONFIG.read_bytes())
    if with_theme:
        (tmp_path / "theme.py").write_text('NAME = "fixture"\nCODE = {}\nUI = {}\n')
    # The gate need not install a second REPL; only its style conversion is stubbed.
    styles = ModuleType("prompt_toolkit.styles")
    monkeypatch.setattr(styles, "Style", Mock(), raising=False)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.styles", styles)
    monkeypatch.chdir(tmp_path.parent)
    namespace = {}
    exec(compile(config.read_bytes(), str(config), "exec"), namespace)  # noqa: S102
    repl = Mock()
    namespace["configure"](repl)
    assert repl.vi_mode is True
    assert repl.confirm_exit is False
    if with_theme:
        repl.use_code_colorscheme.assert_called_once_with("fixture")
        repl.use_ui_colorscheme.assert_called_once_with("fixture")
    else:
        repl.install_code_colorscheme.assert_not_called()
        repl.install_ui_colorscheme.assert_not_called()
