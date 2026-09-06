"""Small Typer registration helpers shared by command modules."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar, TypeVar

import typer
from typer import _click
from typer.core import TyperCommand, TyperGroup

from fmind_dot.errors import DotError
from fmind_dot.state import State

_F = TypeVar("_F", bound=Callable[..., object])


class AliasedGroup(TyperGroup):
    """TyperGroup that displays command aliases inline and sorts visible commands."""

    aliases: ClassVar[dict[str, tuple[str, ...]]] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Preserve an instance-level copy so mutations remain group-local.
        self.aliases: dict[str, tuple[str, ...]] = dict(getattr(self, "aliases", {}))

    def list_commands(self, ctx: _click.Context) -> list[str]:
        return sorted(super().list_commands(ctx))

    def format_commands(self, ctx: _click.Context, formatter: _click.HelpFormatter) -> None:
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or cmd.hidden:
                continue
            aliases = self.aliases.get(subcommand)
            display_name = f"{subcommand} ({', '.join(aliases)})" if aliases else subcommand
            commands.append((display_name, cmd))

        if commands:
            limit = formatter.width - 6 - max(len(item[0]) for item in commands)
            rows = []
            for display_name, cmd in commands:
                rows.append((display_name, cmd.get_short_help_str(limit)))
            if rows:
                with formatter.section("Commands"):
                    formatter.write_dl(rows)

    def format_help(self, ctx: _click.Context, formatter: _click.HelpFormatter) -> None:
        # Temporarily append registered aliases to visible command names so Typer's
        # Rich panel displays them in the first column without polluting descriptions.
        orig_names: dict[str, str | None] = {}
        for name, aliases in self.aliases.items():
            cmd = self.commands.get(name)
            if cmd is not None and aliases:
                orig_names[name] = cmd.name
                cmd.name = f"{name} ({', '.join(aliases)})"
        try:
            super().format_help(ctx, formatter)
        finally:
            for name, orig in orig_names.items():
                cmd = self.commands.get(name)
                if cmd is not None:
                    cmd.name = orig


def _ensure_group_class(parent: typer.Typer) -> type[AliasedGroup]:
    current_cls = parent.info.cls
    if (
        isinstance(current_cls, type)
        and issubclass(current_cls, AliasedGroup)
        and getattr(current_cls, "_isolated", False)
    ):
        return current_cls

    class _BoundGroup(AliasedGroup):
        _isolated = True
        aliases: ClassVar[dict[str, tuple[str, ...]]] = {}

    parent.info.cls = _BoundGroup
    return _BoundGroup


def record_alias(parent: typer.Typer, name: str, *aliases: str) -> None:
    """Record one or more aliases for a canonical command name on a parent Typer application."""
    if not aliases:
        return
    group_cls = _ensure_group_class(parent)
    current = list(group_cls.aliases.get(name, ()))
    for alias in aliases:
        if alias not in current:
            current.append(alias)
    group_cls.aliases[name] = tuple(current)


def add_group(parent: typer.Typer, group: typer.Typer, name: str, *aliases: str) -> None:
    if aliases:
        record_alias(parent, name, *aliases)
    parent.add_typer(group, name=name)
    for alias in aliases:
        parent.add_typer(group, name=alias, hidden=True)


def aliased_command(
    parent: typer.Typer,
    name: str,
    *aliases: str,
    help_text: str | None = None,
    cls: type[TyperCommand] | None = None,
) -> Callable[[_F], _F]:
    if aliases:
        record_alias(parent, name, *aliases)

    def decorate(callback: _F) -> _F:
        parent.command(name=name, help=help_text, cls=cls)(callback)
        for alias in aliases:
            parent.command(name=alias, hidden=True, help=help_text, cls=cls)(callback)
        return callback

    return decorate


def state_from(context: typer.Context) -> State:
    state = context.find_root().obj
    if not isinstance(state, State):
        raise DotError("CLI state is unavailable")
    return state
