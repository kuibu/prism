from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer
from nio import AsyncClient, LoginResponse, SyncResponse
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Prism developer CLI")
console = Console()

DEFAULT_SESSION_FILE = "~/.prism-cli/session.json"


@dataclass
class MatrixSession:
    homeserver: str
    user_id: str
    device_id: str
    access_token: str
    last_sync_token: str | None = None


def _resolve_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _redact_secret(value: str, *, visible: int = 4) -> str:
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * (len(value) - visible) + value[-visible:]


def _load_session(path: Path) -> MatrixSession:
    if not path.exists():
        raise RuntimeError(f"session file not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return MatrixSession(
            homeserver=str(payload["homeserver"]),
            user_id=str(payload["user_id"]),
            device_id=str(payload["device_id"]),
            access_token=str(payload["access_token"]),
            last_sync_token=payload.get("last_sync_token"),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"invalid session file: {path}") from exc


def _save_session(path: Path, session: MatrixSession) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(asdict(session), ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(path)


def _build_authenticated_client(session: MatrixSession) -> AsyncClient:
    client = AsyncClient(session.homeserver, session.user_id)
    client.access_token = session.access_token
    client.user_id = session.user_id
    client.device_id = session.device_id
    return client


def _extract_message_row(room_id: str, event: Any) -> tuple[str, str, str, str] | None:
    source = getattr(event, "source", {})
    if not isinstance(source, dict):
        return None

    event_type = str(source.get("type", ""))
    if event_type != "m.room.message":
        return None

    content = source.get("content", {})
    if not isinstance(content, dict):
        content = {}

    sender = str(source.get("sender", "unknown"))
    body = str(content.get("body", ""))
    ts_value = source.get("origin_server_ts")
    timestamp = "-"

    if isinstance(ts_value, (int, float)):
        timestamp = (
            datetime.fromtimestamp(float(ts_value) / 1000.0, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

    return (room_id, sender, body, timestamp)


@app.command("status")
def status(
    gateway_url: str = "http://localhost:8080",
    session_file: str = DEFAULT_SESSION_FILE,
) -> None:
    """Show local CLI status and stored Matrix session info."""
    session_path = _resolve_path(session_file)
    console.print(f"Gateway: [bold]{gateway_url}[/bold]")
    console.print(f"Session file: [bold]{session_path}[/bold]")

    if not session_path.exists():
        console.print("[yellow]No active Matrix session found.[/yellow]")
        return

    try:
        session = _load_session(session_path)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print("[green]Matrix session loaded.[/green]")
    console.print(f"- homeserver: {session.homeserver}")
    console.print(f"- user_id: {session.user_id}")
    console.print(f"- device_id: {session.device_id}")
    console.print(f"- access_token: {_redact_secret(session.access_token)}")
    console.print(f"- last_sync_token: {session.last_sync_token or '(none)'}")


@app.command("login")
def login(
    user: str = typer.Option(..., "--user", "-u", help="Matrix user id or localpart"),
    password: str = typer.Option(
        ...,
        "--password",
        "-p",
        prompt=True,
        hide_input=True,
        help="Matrix account password",
    ),
    homeserver: str = typer.Option(
        "http://localhost:8008",
        "--homeserver",
        "-H",
        help="Matrix homeserver URL",
    ),
    device_name: str = typer.Option("prism-cli", "--device-name", help="Device name for login"),
    session_file: str = typer.Option(
        DEFAULT_SESSION_FILE,
        "--session-file",
        help="Path to session json file",
    ),
) -> None:
    """Login to Matrix and persist access token locally."""
    session_path = _resolve_path(session_file)
    asyncio.run(
        _login_async(
            user=user,
            password=password,
            homeserver=homeserver,
            device_name=device_name,
            session_path=session_path,
        )
    )


async def _login_async(
    *,
    user: str,
    password: str,
    homeserver: str,
    device_name: str,
    session_path: Path,
) -> None:
    client = AsyncClient(homeserver, user)
    try:
        response = await client.login(password=password, device_name=device_name)
        if not isinstance(response, LoginResponse):
            reason = str(getattr(response, "message", "login_failed"))
            console.print(f"[red]Login failed:[/red] {reason}")
            raise typer.Exit(code=1)

        session = MatrixSession(
            homeserver=homeserver,
            user_id=response.user_id,
            device_id=response.device_id,
            access_token=response.access_token,
            last_sync_token=None,
        )
        _save_session(session_path, session)
        console.print("[green]Login successful.[/green]")
        console.print(f"user_id: {session.user_id}")
        console.print(f"device_id: {session.device_id}")
        console.print(f"session saved to: {session_path}")
    finally:
        await client.close()


@app.command("sync")
def sync(
    since: str | None = typer.Option(None, "--since", help="Sync token override"),
    timeout_ms: int = typer.Option(3000, "--timeout-ms", min=0, max=60000),
    full_state: bool = typer.Option(False, "--full-state"),
    room_id: str | None = typer.Option(None, "--room-id", help="Only show one room"),
    max_events: int = typer.Option(50, "--max-events", min=1, max=500),
    session_file: str = typer.Option(
        DEFAULT_SESSION_FILE,
        "--session-file",
        help="Path to session json file",
    ),
) -> None:
    """Run one /sync and print message events."""
    session_path = _resolve_path(session_file)
    asyncio.run(
        _sync_async(
            since=since,
            timeout_ms=timeout_ms,
            full_state=full_state,
            room_id=room_id,
            max_events=max_events,
            session_path=session_path,
        )
    )


async def _sync_async(
    *,
    since: str | None,
    timeout_ms: int,
    full_state: bool,
    room_id: str | None,
    max_events: int,
    session_path: Path,
) -> None:
    try:
        session = _load_session(session_path)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    client = _build_authenticated_client(session)
    try:
        sync_token = since if since is not None else session.last_sync_token
        response = await client.sync(timeout=timeout_ms, since=sync_token, full_state=full_state)
        if not isinstance(response, SyncResponse):
            reason = str(getattr(response, "message", "sync_failed"))
            console.print(f"[red]Sync failed:[/red] {reason}")
            raise typer.Exit(code=1)

        session.last_sync_token = response.next_batch
        _save_session(session_path, session)

        table = Table(title="Matrix Sync Messages")
        table.add_column("Room")
        table.add_column("Sender")
        table.add_column("Body")
        table.add_column("TS (UTC)")

        count = 0
        for joined_room_id, joined_room in response.rooms.join.items():
            if room_id is not None and joined_room_id != room_id:
                continue
            for event in joined_room.timeline.events:
                row = _extract_message_row(joined_room_id, event)
                if row is None:
                    continue
                table.add_row(*row)
                count += 1
                if count >= max_events:
                    break
            if count >= max_events:
                break

        console.print(f"[green]Sync ok[/green], next_batch={response.next_batch}")
        if count == 0:
            console.print("[yellow]No message events in this sync response.[/yellow]")
            return
        console.print(table)
    finally:
        await client.close()


@app.command("send")
def send(
    room_id: str = typer.Argument(..., help="Target Matrix room id"),
    message: str = typer.Argument(..., help="Message body"),
    session_file: str = typer.Option(
        DEFAULT_SESSION_FILE,
        "--session-file",
        help="Path to session json file",
    ),
) -> None:
    """Send one m.room.message text event."""
    session_path = _resolve_path(session_file)
    asyncio.run(
        _send_async(
            room_id=room_id,
            message=message,
            session_path=session_path,
        )
    )


async def _send_async(*, room_id: str, message: str, session_path: Path) -> None:
    try:
        session = _load_session(session_path)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    client = _build_authenticated_client(session)
    try:
        response = await client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": message},
        )

        event_id = getattr(response, "event_id", None)
        if event_id is None:
            reason = str(getattr(response, "message", "send_failed"))
            console.print(f"[red]Send failed:[/red] {reason}")
            raise typer.Exit(code=1)

        console.print("[green]Message sent.[/green]")
        console.print(f"room_id: {room_id}")
        console.print(f"event_id: {event_id}")
    finally:
        await client.close()


def run() -> None:
    app()


if __name__ == "__main__":
    run()
