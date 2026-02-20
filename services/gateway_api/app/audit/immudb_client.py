import asyncio
from typing import Any


class ImmudbClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
        retry_attempts: int,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = max(1, retry_attempts)

    async def health(self) -> dict[str, Any]:
        last_error: str | None = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                connect_task = asyncio.open_connection(self.host, self.port)
                _, writer = await asyncio.wait_for(connect_task, timeout=self.timeout_seconds)
                writer.close()
                await writer.wait_closed()
                return {
                    "reachable": True,
                    "host": self.host,
                    "port": self.port,
                    "attempt": attempt,
                }
            except TimeoutError:
                last_error = "timeout"
            except OSError as exc:
                last_error = str(exc)

            if attempt < self.retry_attempts:
                await asyncio.sleep(0.2 * attempt)

        return {
            "reachable": False,
            "error": last_error or "immudb_unreachable",
            "host": self.host,
            "port": self.port,
            "attempt": self.retry_attempts,
        }
