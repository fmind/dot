# Cyclopts & Existing Typer CLIs

Use `cyclopts>=5.5.2` when multi-command trees, native Python 3.12+ union/literal/Pydantic annotations, or docstring parameter help outgrow stdlib `argparse` ([CLI defaults](../GUIDE.md#defaults-for-new-clis) still govern streams, exits, and JSON):

- **Typed dispatch & clean streams**: configure `app = App(help_format="plaintext")` on agent-facing CLIs so union types, `Literal`, dataclasses, and Pydantic v2 models parse directly without Click parameter adapters or mandatory Rich tracebacks.
- **Test in-process**: invoke `app(["subcmd", "--flag"], result_action="return_value")` with captured streams, verifying exit code `2` on validation errors and pure JSON on stdout when `--json` is set.
- **Existing Typer repos**: keep Typer in place when already adopted, pinning `typer>=0.N,<0.N+1`, adding `@app.callback()`, and setting `rich_markup_mode=None` plus `pretty_exceptions_enable=False` so Rich panels never corrupt piped or `NO_COLOR` streams.

Docs: [Cyclopts](https://cyclopts.readthedocs.io/en/stable/) ([releases](https://github.com/BrianPugh/cyclopts/releases)) · [Typer releases](https://typer.tiangolo.com/release-notes/).
