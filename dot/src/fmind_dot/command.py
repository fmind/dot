"""Standard-library command tree: argparse parsers with a public structure, plain help, and Fish candidates."""

from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fmind_dot.state import State

Handler = Callable[["State", argparse.Namespace], Any]
COMPLETE_VARIABLE = "_DOT_COMPLETE"
FISH_COMPLETION = f"""\
function __dot_prepare_candidates
    set -g __dot_last_candidates ({COMPLETE_VARIABLE}="$(commandline --cut-at-cursor --current-token)" dot (commandline --cut-at-cursor --current-process --tokens-expanded)[2..])
    set -q __dot_last_candidates[1]
end
complete --command dot --no-files --condition __dot_prepare_candidates --arguments '(printf "%s\\n" $__dot_last_candidates)'
"""


class _HelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog: str, **kwargs: Any) -> None:
        width = shutil.get_terminal_size().columns - 2 if sys.stdout.isatty() else 160
        super().__init__(prog, max_help_position=28, width=width, **kwargs)

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        fill = super()._fill_text
        return "\n\n".join(fill(part, width, indent) for part in text.split("\n\n"))


class Parser(argparse.ArgumentParser):
    """One node of the command tree; `children` and `arguments` expose it to completions and tests."""

    def __init__(self, *, summary: str = "", **kwargs: Any) -> None:
        self.summary = summary
        self.arguments: list[argparse.Action] = []
        self.children: dict[str, Parser] = {}
        self._commands: Any = None
        super().__init__(
            description=summary, formatter_class=_HelpFormatter, allow_abbrev=False, suggest_on_error=True, **kwargs
        )

    def add_argument(self, *args: Any, **kwargs: Any) -> argparse.Action:
        action = super().add_argument(*args, **kwargs)
        self.arguments.append(action)
        return action

    def show_help(self, state: State, _args: argparse.Namespace) -> None:
        self.print_help(state.stdout)

    def _child(self, name: str, summary: str, *, epilog: str) -> Parser:
        if self._commands is None:
            self._commands = self.add_subparsers(title="commands", metavar="COMMAND")
        child: Parser = self._commands.add_parser(name, summary=summary, epilog=epilog or None, help=summary)
        self.children[name] = child
        return child

    def group(
        self, name: str, summary: str, *, handler: Handler | None = None, config: bool = False, epilog: str = ""
    ) -> Parser:
        """Add a command group; without a command it prints its help, or runs `handler`."""
        child = self._child(name, summary, epilog=epilog)
        child.set_defaults(handler=handler or child.show_help, needs_config=config, parser=child)
        return child

    def command(self, name: str, summary: str, handler: Handler, *, config: bool = True, epilog: str = "") -> Parser:
        """Add a leaf command; `config` validates dot.yaml before the handler runs."""
        child = self._child(name, summary, epilog=epilog)
        child.set_defaults(handler=handler, needs_config=config, parser=child)
        return child


def add_json(parser: Parser) -> None:
    """One definition keeps every structured-output flag documented identically."""
    parser.add_argument("-j", "--json", dest="as_json", action="store_true", help="Emit structured JSON")


def _takes_value(action: argparse.Action) -> bool:
    return bool(action.option_strings) and action.nargs != 0


def candidates(root: Parser, words: list[str]) -> list[tuple[str, str]]:
    """Complete the last of `words` (the words after the program name) as (value, description) pairs."""
    *completed, current = words or [""]
    parser, pending, positionals_used = root, None, 0
    for word in completed:
        if pending is not None:
            pending = None
        elif word == "--":
            return []
        elif word.startswith("-"):
            if "=" not in word:
                option = next((item for item in parser.arguments if word in item.option_strings), None)
                pending = option if option is not None and _takes_value(option) else None
        elif word in parser.children and positionals_used == 0:
            parser = parser.children[word]
        else:
            positionals_used += 1
    if pending is not None:
        found = [(str(choice), "") for choice in pending.choices or ()]
    elif current.startswith("--") and "=" in current:
        flag, prefix = current.split("=", 1)
        option = next((item for item in parser.arguments if flag in item.option_strings and _takes_value(item)), None)
        return [
            (f"{flag}={c}", "")
            for c in (option.choices if option is not None else None) or ()
            if str(c).startswith(prefix)
        ]
    elif current.startswith("-"):
        found = [
            (flag, " ".join((item.help or "").split())) for item in parser.arguments for flag in item.option_strings
        ]
    else:
        found = [(name, child.summary) for name, child in parser.children.items()] if positionals_used == 0 else []
        positionals = [item for item in parser.arguments if not item.option_strings]
        active = (
            positionals[positionals_used]
            if positionals_used < len(positionals)
            else (positionals[-1] if positionals and positionals[-1].nargs in {"*", "+"} else None)
        )
        if active is not None:
            found += [(str(choice), "") for choice in active.choices or ()]
    return [(value, description) for value, description in found if value.startswith(current)]
