from __future__ import annotations

import json
import mimetypes
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Prism developer CLI")
console = Console()

DEFAULT_GATEWAY_URL = "http://localhost:8080/api/v1"
DEFAULT_SESSION_FILE = "~/.prism-cli/session.json"


@dataclass
class MatrixSession:
    gateway_url: str
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


def _normalize_username(raw: str) -> str:
    value = raw.strip()
    if value == "":
        return ""
    if value.startswith("@"):
        tail = value[1:]
        colon_index = tail.find(":")
        return tail[:colon_index] if colon_index >= 0 else tail
    return value


def _load_session(path: Path) -> MatrixSession:
    if not path.exists():
        raise RuntimeError(f"session file not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return MatrixSession(
            gateway_url=str(payload.get("gateway_url", DEFAULT_GATEWAY_URL)),
            homeserver=str(payload.get("homeserver", "n/a")),
            user_id=str(payload["user_id"]),
            device_id=str(payload.get("device_id", "")),
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
    tmp.write_text(
        json.dumps(asdict(session), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(path)


def _request_json(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    request_headers = {"content-type": "application/json"}
    if headers:
        request_headers.update(headers)

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method=method, url=url, json=payload, headers=request_headers
            )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"request_failed: {exc}") from exc

    try:
        data = response.json() if response.content else {}
    except ValueError:
        data = {"raw": response.text}

    if response.is_error:
        detail = data.get("detail") if isinstance(data, dict) else data
        raise RuntimeError(f"{response.status_code} {response.reason_phrase}: {detail}")
    return data if isinstance(data, dict) else {"data": data}


@app.command("status")
def status(
    gateway_url: str = DEFAULT_GATEWAY_URL,
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
    console.print(f"- gateway_url: {session.gateway_url}")
    console.print(f"- homeserver: {session.homeserver}")
    console.print(f"- user_id: {session.user_id}")
    console.print(f"- device_id: {session.device_id or '(unknown)'}")
    console.print(f"- access_token: {_redact_secret(session.access_token)}")
    console.print(f"- last_sync_token: {session.last_sync_token or '(none)'}")


@app.command("register")
def register(
    user: str = typer.Option(..., "--user", "-u", help="Matrix user id or localpart"),
    password: str = typer.Option(
        ...,
        "--password",
        "-p",
        prompt=True,
        hide_input=True,
        help="Matrix account password",
    ),
    gateway_url: str = typer.Option(
        DEFAULT_GATEWAY_URL, "--gateway-url", help="Gateway API base URL"
    ),
    homeserver: str = typer.Option(
        "http://localhost:8008",
        "--homeserver",
        "-H",
        help="Homeserver URL metadata for display",
    ),
    session_file: str = typer.Option(
        DEFAULT_SESSION_FILE, "--session-file", help="Session file path"
    ),
) -> None:
    """Register via gateway and persist Matrix access token."""
    username = _normalize_username(user)
    if username == "":
        console.print("[red]username is required[/red]")
        raise typer.Exit(code=1)

    endpoint = f"{gateway_url.rstrip('/')}/matrix/register"
    try:
        payload = _request_json(
            method="POST",
            url=endpoint,
            payload={"username": username, "password": password},
        )
    except RuntimeError as exc:
        console.print(f"[red]Register failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    _save_login_result(
        payload=payload,
        session_path=_resolve_path(session_file),
        gateway_url=gateway_url,
        homeserver=homeserver,
        success_prefix="Register successful.",
    )


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
    gateway_url: str = typer.Option(
        DEFAULT_GATEWAY_URL, "--gateway-url", help="Gateway API base URL"
    ),
    homeserver: str = typer.Option(
        "http://localhost:8008",
        "--homeserver",
        "-H",
        help="Homeserver URL metadata for display",
    ),
    session_file: str = typer.Option(
        DEFAULT_SESSION_FILE, "--session-file", help="Session file path"
    ),
) -> None:
    """Login via gateway and persist Matrix access token."""
    username = _normalize_username(user)
    if username == "":
        console.print("[red]username is required[/red]")
        raise typer.Exit(code=1)

    endpoint = f"{gateway_url.rstrip('/')}/matrix/login"
    try:
        payload = _request_json(
            method="POST",
            url=endpoint,
            payload={"username": username, "password": password},
        )
    except RuntimeError as exc:
        console.print(f"[red]Login failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    _save_login_result(
        payload=payload,
        session_path=_resolve_path(session_file),
        gateway_url=gateway_url,
        homeserver=homeserver,
        success_prefix="Login successful.",
    )


def _save_login_result(
    *,
    payload: dict[str, Any],
    session_path: Path,
    gateway_url: str,
    homeserver: str,
    success_prefix: str,
) -> None:
    user_id = payload.get("user_id")
    access_token = payload.get("access_token")
    if (
        not isinstance(user_id, str)
        or user_id == ""
        or not isinstance(access_token, str)
    ):
        console.print("[red]gateway returned invalid auth response[/red]")
        raise typer.Exit(code=1)

    session = MatrixSession(
        gateway_url=gateway_url.rstrip("/"),
        homeserver=homeserver.rstrip("/"),
        user_id=user_id,
        device_id=str(payload.get("device_id", "")),
        access_token=access_token,
        last_sync_token=None,
    )
    _save_session(session_path, session)
    console.print(f"[green]{success_prefix}[/green]")
    console.print(f"user_id: {session.user_id}")
    console.print(f"device_id: {session.device_id or '(unknown)'}")
    console.print(f"session saved to: {session_path}")


@app.command("sync")
def sync(
    since: str | None = typer.Option(None, "--since", help="Sync token override"),
    timeout_ms: int = typer.Option(3000, "--timeout-ms", min=0, max=60000),
    full_state: bool = typer.Option(False, "--full-state"),
    room_id: str | None = typer.Option(None, "--room-id", help="Only show one room"),
    max_events: int = typer.Option(50, "--max-events", min=1, max=500),
    session_file: str = typer.Option(
        DEFAULT_SESSION_FILE, "--session-file", help="Session file path"
    ),
) -> None:
    """Run one gateway-backed /sync and print message events."""
    session_path = _resolve_path(session_file)
    try:
        session = _load_session(session_path)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    params: dict[str, Any] = {"timeout_ms": timeout_ms, "full_state": full_state}
    sync_token = since if since is not None else session.last_sync_token
    if sync_token:
        params["since"] = sync_token
    if room_id:
        params["room_id"] = room_id

    query = str(httpx.QueryParams(params))
    endpoint = f"{session.gateway_url}/matrix/sync"
    if query:
        endpoint = f"{endpoint}?{query}"

    try:
        payload = _request_json(
            method="GET",
            url=endpoint,
            headers={"authorization": f"Bearer {session.access_token}"},
        )
    except RuntimeError as exc:
        console.print(f"[red]Sync failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    next_batch = payload.get("next_batch")
    if isinstance(next_batch, str) and next_batch != "":
        session.last_sync_token = next_batch
        _save_session(session_path, session)

    rows = _extract_sync_rows(payload, room_id=room_id, max_events=max_events)
    console.print(
        f"[green]Sync ok[/green], next_batch={session.last_sync_token or '(none)'}"
    )
    if not rows:
        console.print("[yellow]No message events in this sync response.[/yellow]")
        return

    table = Table(title="Matrix Sync Messages")
    table.add_column("Room")
    table.add_column("Sender")
    table.add_column("Body")
    table.add_column("TS (UTC)")
    for row in rows:
        table.add_row(*row)
    console.print(table)


def _extract_sync_rows(
    payload: dict[str, Any],
    *,
    room_id: str | None,
    max_events: int,
) -> list[tuple[str, str, str, str]]:
    joined = payload.get("rooms", {}).get("join", {})
    if not isinstance(joined, dict):
        return []

    rows: list[tuple[str, str, str, str]] = []
    for joined_room_id, joined_room in joined.items():
        if room_id is not None and joined_room_id != room_id:
            continue
        if not isinstance(joined_room_id, str) or not isinstance(joined_room, dict):
            continue

        events = joined_room.get("timeline", {}).get("events", [])
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "m.room.message":
                continue
            sender = str(event.get("sender", "unknown"))
            body = str(event.get("content", {}).get("body", ""))
            timestamp = "-"
            ts_value = event.get("origin_server_ts")
            if isinstance(ts_value, (int, float)):
                timestamp = (
                    datetime.fromtimestamp(float(ts_value) / 1000.0, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                )
            rows.append((joined_room_id, sender, body, timestamp))
            if len(rows) >= max_events:
                return rows
    return rows


@app.command("send")
def send(
    room_id: str = typer.Argument(..., help="Target Matrix room id"),
    message: str = typer.Argument(..., help="Message body"),
    session_file: str = typer.Option(
        DEFAULT_SESSION_FILE, "--session-file", help="Session file path"
    ),
) -> None:
    """Send one text message via gateway."""
    session_path = _resolve_path(session_file)
    try:
        session = _load_session(session_path)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    encoded_room_id = quote(room_id, safe="")
    endpoint = f"{session.gateway_url}/matrix/rooms/{encoded_room_id}/messages"
    try:
        response = _request_json(
            method="POST",
            url=endpoint,
            payload={"body": message},
            headers={"authorization": f"Bearer {session.access_token}"},
        )
    except RuntimeError as exc:
        console.print(f"[red]Send failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    event_id = response.get("event_id")
    if not isinstance(event_id, str) or event_id == "":
        console.print("[red]gateway returned invalid send response[/red]")
        raise typer.Exit(code=1)

    console.print("[green]Message sent.[/green]")
    console.print(f"room_id: {room_id}")
    console.print(f"event_id: {event_id}")


@app.command("send-file")
def send_file(
    room_id: str = typer.Argument(..., help="Target Matrix room id"),
    file_path: str = typer.Argument(..., help="File path to upload"),
    session_file: str = typer.Option(
        DEFAULT_SESSION_FILE, "--session-file", help="Session file path"
    ),
) -> None:
    """Upload a file via gateway and send it into the room."""
    session_path = _resolve_path(session_file)
    try:
        session = _load_session(session_path)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    source = Path(file_path).expanduser().resolve()
    if not source.exists() or not source.is_file():
        console.print(f"[red]file not found:[/red] {source}")
        raise typer.Exit(code=1)

    mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    encoded_room_id = quote(room_id, safe="")
    endpoint = f"{session.gateway_url}/matrix/rooms/{encoded_room_id}/files"

    try:
        with source.open("rb") as fh, httpx.Client(timeout=30.0) as client:
            response = client.post(
                endpoint,
                headers={"authorization": f"Bearer {session.access_token}"},
                files={"file": (source.name, fh, mime_type)},
            )
    except (OSError, httpx.HTTPError) as exc:
        console.print(f"[red]Upload failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    try:
        payload = response.json() if response.content else {}
    except ValueError:
        payload = {"raw": response.text}

    if response.is_error:
        detail = payload.get("detail") if isinstance(payload, dict) else payload
        console.print(
            f"[red]Upload failed:[/red] {response.status_code} {response.reason_phrase}: {detail}"
        )
        raise typer.Exit(code=1)

    event_id = payload.get("event_id")
    content_uri = payload.get("content_uri")
    console.print("[green]File message sent.[/green]")
    console.print(f"room_id: {room_id}")
    console.print(f"file: {source.name}")
    console.print(f"event_id: {event_id}")
    console.print(f"content_uri: {content_uri}")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
