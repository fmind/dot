"""Configuration for ptpython.

Docs: https://github.com/prompt-toolkit/ptpython
"""

import importlib.util
from pathlib import Path
from typing import Any

from prompt_toolkit.styles import Style

# Colours live in the theme, not here. theme.py is fetched from
# github.com/fmind/theme by .chezmoiexternal.toml.tmpl and exports two
# prompt_toolkit style dicts, CODE and UI. It sits next to this file rather than
# on sys.path, so it is loaded by location; ptpython keeps its own defaults if
# it is missing, which is what a fresh checkout looks like before the first
# `chezmoi apply` has fetched the externals.


def _load_theme() -> Any | None:
    """Import theme.py from beside this file, or None if it is not there yet."""
    # ptpython execs this config without __file__, but compiles it with its path.
    theme_path = Path(_load_theme.__code__.co_filename).with_name("theme.py")
    if not theme_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("ptpython_theme", theme_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure(repl) -> None:
    """Configure ptpython REPL."""
    # --- Vi Mode ---
    repl.vi_mode = True
    # --- Behavior ---
    repl.confirm_exit = False
    # --- UI Settings ---
    repl.enable_mouse_support = True
    repl.highlight_matching_parenthesis = True
    repl.prompt_style = "ipython"
    repl.show_docstring = True
    repl.show_line_numbers = True
    repl.show_signature = True
    # --- Theme ---
    theme = _load_theme()
    if theme is not None:
        repl.install_code_colorscheme(theme.NAME, Style.from_dict(theme.CODE))
        repl.use_code_colorscheme(theme.NAME)
        repl.install_ui_colorscheme(theme.NAME, Style.from_dict(theme.UI))
        repl.use_ui_colorscheme(theme.NAME)
    # --- Completion & Suggestion ---
    repl.enable_auto_suggest = True
    repl.enable_history_search = True
    repl.enable_fuzzy_completion = True
