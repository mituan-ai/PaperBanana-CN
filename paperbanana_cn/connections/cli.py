"""Typer commands for persistent connection profiles."""

from __future__ import annotations

import os
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from paperbanana_cn.connections.manager import ConnectionManager
from paperbanana_cn.connections.models import ConnectionProfile, ConnectionRole
from paperbanana_cn.connections.resolver import load_runtime_settings
from paperbanana_cn.connections.testing import (
    ConnectionTestError,
    test_connection,
    validate_connection,
)
from paperbanana_cn.core.config import Settings

console = Console()

connections_app = typer.Typer(
    name="connections",
    help="Manage persistent VLM and image connection profiles.",
    no_args_is_help=True,
)


def connection_role(value: str) -> ConnectionRole:
    try:
        return ConnectionRole(value.lower())
    except ValueError:
        console.print("[red]Role must be 'vlm' or 'image'.[/red]")
        raise typer.Exit(2)


def validate_connection_options(
    *,
    vlm_connection: str | None,
    image_connection: str | None,
    legacy_connections: bool,
    legacy_provider_options: bool,
) -> None:
    if legacy_provider_options and not legacy_connections:
        console.print(
            "[red]Error: provider/model override options require --legacy-connections.[/red]"
        )
        raise typer.Exit(1)
    if (vlm_connection or image_connection) and legacy_connections:
        console.print(
            "[red]Error: saved connection IDs cannot be combined with --legacy-connections.[/red]"
        )
        raise typer.Exit(1)


def load_cli_runtime_settings(
    *,
    config: str | None,
    overrides: dict,
    vlm_connection: str | None,
    image_connection: str | None,
    legacy_connections: bool,
    required_roles: tuple[ConnectionRole, ...] = (
        ConnectionRole.VLM,
        ConnectionRole.IMAGE,
    ),
) -> Settings:
    try:
        return load_runtime_settings(
            config_path=config,
            overrides=overrides,
            vlm_profile_id=vlm_connection,
            image_profile_id=image_connection,
            legacy=legacy_connections,
            required_roles=required_roles,
        )
    except (OSError, ValueError) as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@connections_app.command("list")
def connections_list() -> None:
    """List saved connection profiles without exposing credentials."""
    manager = ConnectionManager()
    config = manager.load()
    table = Table("Active", "Role", "Name", "Provider", "Model", "Base URL", "ID")
    for profile in config.profiles:
        active_id = (
            config.active_vlm_profile_id
            if profile.role == ConnectionRole.VLM
            else config.active_image_profile_id
        )
        table.add_row(
            "*" if profile.id == active_id else "",
            profile.role.value,
            profile.name,
            profile.provider,
            profile.model,
            profile.base_url or "",
            profile.id,
        )
    console.print(table)


@connections_app.command("add")
def connections_add(
    role: str = typer.Option(..., "--role", help="Connection role: vlm or image"),
    name: str = typer.Option(..., "--name", help="Profile name"),
    provider: str = typer.Option(..., "--provider", help="Existing provider adapter"),
    model: str = typer.Option(..., "--model", help="Exact model identifier"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Custom HTTP(S) base URL"),
    timeout: float = typer.Option(180.0, "--timeout", min=1, max=1800),
    size_mode: Optional[str] = typer.Option(
        None,
        "--size-mode",
        help="Image sizing: native_tier, explicit_pixels, fixed, or prompt_hint",
    ),
    no_api_key: bool = typer.Option(False, "--no-api-key", help="Store no API key"),
    api_key_env: Optional[str] = typer.Option(
        None,
        "--api-key-env",
        help="Read the API key from this environment variable (for CI)",
    ),
) -> None:
    """Create and activate a connection profile."""
    parsed_role = connection_role(role)
    if no_api_key and api_key_env:
        console.print("[red]Error: --no-api-key and --api-key-env are mutually exclusive.[/red]")
        raise typer.Exit(1)
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            console.print(f"[red]Error: environment variable {api_key_env} is not set.[/red]")
            raise typer.Exit(1)
    else:
        api_key = None if no_api_key else typer.prompt("API key", hide_input=True)
    profile = ConnectionProfile(
        name=name,
        role=parsed_role,
        provider=provider,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout,
        image_size_mode=size_mode if parsed_role == ConnectionRole.IMAGE else None,
    )
    ConnectionManager().save_profile(profile, api_key=api_key)
    console.print(f"[green]Saved and activated {parsed_role.value} profile:[/green] {profile.id}")


@connections_app.command("edit")
def connections_edit(
    profile_id: str = typer.Argument(..., help="Connection profile ID"),
    name: Optional[str] = typer.Option(None, "--name"),
    provider: Optional[str] = typer.Option(None, "--provider"),
    model: Optional[str] = typer.Option(None, "--model"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    timeout: Optional[float] = typer.Option(None, "--timeout", min=1, max=1800),
    size_mode: Optional[str] = typer.Option(None, "--size-mode"),
    replace_key: bool = typer.Option(False, "--replace-key", help="Prompt for a new API key"),
    clear_key: bool = typer.Option(False, "--clear-key", help="Remove the saved API key"),
) -> None:
    """Edit profile metadata and optionally replace its credential."""
    if replace_key and clear_key:
        console.print("[red]Error: --replace-key and --clear-key are mutually exclusive.[/red]")
        raise typer.Exit(1)
    manager = ConnectionManager()
    config = manager.load()
    profile = next((item for item in config.profiles if item.id == profile_id), None)
    if profile is None:
        console.print(f"[red]Connection profile not found: {profile_id}[/red]")
        raise typer.Exit(1)
    updates = {
        key: value
        for key, value in {
            "name": name,
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "timeout_seconds": timeout,
            "image_size_mode": size_mode,
        }.items()
        if value is not None
    }
    key = typer.prompt("New API key", hide_input=True) if replace_key else None
    manager.save_profile(
        profile.model_copy(update=updates),
        api_key=key,
        clear_api_key=clear_key,
    )
    console.print("[green]Connection profile updated.[/green]")


@connections_app.command("use")
def connections_use(
    role: str = typer.Option(..., "--role", help="Connection role: vlm or image"),
    profile_id: str = typer.Argument(..., help="Connection profile ID"),
) -> None:
    """Select the active profile for one role."""
    ConnectionManager().set_active(connection_role(role), profile_id)
    console.print("[green]Active connection updated.[/green]")


@connections_app.command("delete")
def connections_delete(
    profile_id: str = typer.Argument(..., help="Connection profile ID"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
) -> None:
    """Delete a profile and its unshared credential."""
    if not yes and not typer.confirm(f"Delete connection profile {profile_id}?"):
        raise typer.Abort()
    ConnectionManager().delete_profile(profile_id)
    console.print("[green]Connection profile deleted.[/green]")


@connections_app.command("test")
def connections_test(
    profile_id: str = typer.Argument(..., help="Connection profile ID"),
    paid: bool = typer.Option(False, "--paid", help="Allow an image generation request"),
) -> None:
    """Validate a profile; image network tests require --paid."""
    manager = ConnectionManager()
    profile = next((item for item in manager.load().profiles if item.id == profile_id), None)
    if profile is None:
        console.print(f"[red]Connection profile not found: {profile_id}[/red]")
        raise typer.Exit(1)
    try:
        if profile.role == ConnectionRole.IMAGE and not paid:
            validate_connection(manager, profile)
            console.print(
                "[yellow]Configuration is valid. Use --paid for a real image test.[/yellow]"
            )
            return
        test_connection(manager, profile)
    except ConnectionTestError as exc:
        console.print(f"[red]Connection test failed ({exc.kind.value}): {exc}[/red]")
        raise typer.Exit(1)
    console.print("[green]Connection test succeeded.[/green]")


@connections_app.command("import-legacy")
def connections_import_legacy(
    config: Optional[str] = typer.Option(None, "--config", help="Optional upstream YAML"),
) -> None:
    """Import the currently resolved upstream VLM and image settings once."""
    from paperbanana_cn.providers.registry import ProviderRegistry

    settings = Settings.from_yaml(config) if config else Settings()
    providers = [
        (ConnectionRole.VLM, ProviderRegistry.create_vlm(settings), settings.vlm_provider),
        (
            ConnectionRole.IMAGE,
            ProviderRegistry.create_image_gen(settings),
            settings.image_provider,
        ),
    ]
    manager = ConnectionManager()
    for role, runtime_provider, provider_name in providers:
        api_key = getattr(runtime_provider, "_api_key", None)
        profile = ConnectionProfile(
            name=f"Imported {role.value}",
            role=role,
            provider=provider_name,
            base_url=getattr(runtime_provider, "_base_url", None),
            model=runtime_provider.model_name,
        )
        manager.save_profile(profile, api_key=api_key)
    console.print("[green]Imported and activated both legacy connections.[/green]")
