from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="Prism developer CLI")
console = Console()


@app.command("status")
def status(gateway_url: str = "http://localhost:8080") -> None:
    """Iteration 1 placeholder command."""
    console.print(
        f"Gateway expected at [bold]{gateway_url}[/bold]. "
        "Matrix login/sync/send commands will be implemented in Iteration 4."
    )


def run() -> None:
    app()


if __name__ == "__main__":
    run()
