from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from app.audit.schemas import AuditEvent, AuditEventCreate, AuditQuery, AuditVerifyResponse
from app.audit.verification import compute_chain_hash, sha256_hex, verify_chain


class ImmudbOperationError(RuntimeError):
    """Raised when an immudb operation fails."""


class ImmudbClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
        retry_attempts: int,
        username: str,
        password: str,
        database: str,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = max(1, retry_attempts)
        self.username = username
        self.password = password
        self.database = database

        self._schema_ready = False
        self._schema_lock = asyncio.Lock()
        self._valid_event_predicate = (
            "chain_hash <> '' AND ts_ms > 0 AND actor_type <> '' AND decision <> ''"
        )

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

    async def append_audit_event(self, request: AuditEventCreate) -> AuditEvent:
        await self._ensure_schema()

        ts = datetime.now(timezone.utc)
        ts_ms = int(ts.timestamp() * 1000)
        prev_hash = await asyncio.to_thread(self._get_latest_chain_hash_sync)
        input_hash = request.input_hash or sha256_hex(request.input_data)
        output_hash = request.output_hash or sha256_hex(request.output_data)

        event_id = str(uuid4())
        payload_for_hash = {
            "event_id": event_id,
            "ts_ms": ts_ms,
            "actor_type": request.actor_type.value,
            "actor_id": request.actor_id,
            "action_type": request.action_type,
            "resource_type": request.resource_type,
            "resource_id": request.resource_id,
            "decision": request.decision.value,
            "reason_code": request.reason_code,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "prev_hash": prev_hash,
            "signature": request.signature,
            "user_id": request.user_id,
            "room_id": request.room_id,
            "metadata": request.metadata,
        }
        chain_hash = compute_chain_hash(payload_for_hash)

        event = AuditEvent(
            event_id=event_id,
            ts=ts,
            ts_ms=ts_ms,
            actor_type=request.actor_type,
            actor_id=request.actor_id,
            action_type=request.action_type,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            decision=request.decision,
            reason_code=request.reason_code,
            input_hash=input_hash,
            output_hash=output_hash,
            prev_hash=prev_hash,
            chain_hash=chain_hash,
            signature=request.signature,
            user_id=request.user_id,
            room_id=request.room_id,
            metadata=request.metadata,
        )

        tx_id = await asyncio.to_thread(self._insert_event_sync, event)
        return event.model_copy(update={"immudb_tx_id": tx_id})

    async def query_audit_events(self, query: AuditQuery) -> list[AuditEvent]:
        await self._ensure_schema()
        rows = await asyncio.to_thread(self._query_events_sync, query, True)
        events: list[AuditEvent] = []
        for row in rows:
            try:
                events.append(self._row_to_event(row))
            except (TypeError, ValueError):
                continue
        return events

    async def verify_audit_chain(self, query: AuditQuery) -> AuditVerifyResponse:
        await self._ensure_schema()
        rows = await asyncio.to_thread(self._query_events_sync, query, False)

        if not rows:
            state = await asyncio.to_thread(self._current_state_sync)
            return AuditVerifyResponse(
                verified=True,
                checked_events=0,
                state_tx_id=state["tx_id"],
                state_tx_hash=state["tx_hash"],
            )

        valid_pairs: list[tuple[int, AuditEvent]] = []
        for row in rows:
            try:
                valid_pairs.append((int(row[0]), self._row_to_event(row)))
            except (TypeError, ValueError):
                continue

        if not valid_pairs:
            state = await asyncio.to_thread(self._current_state_sync)
            return AuditVerifyResponse(
                verified=True,
                checked_events=0,
                state_tx_id=state["tx_id"],
                state_tx_hash=state["tx_hash"],
            )

        events = [event for _, event in valid_pairs]
        verified = True
        broken_event_id: str | None = None
        reason: str | None = None

        # For filtered queries, selected events may not be contiguous in the global chain.
        # Validate each event against its real predecessor in the full table.
        for row_id, event in valid_pairs:
            expected_prev_hash = await asyncio.to_thread(
                self._get_prev_hash_before_id_sync,
                row_id,
            )
            item_verified, _, item_reason = verify_chain(
                [event],
                expected_first_prev_hash=expected_prev_hash,
            )
            if item_verified:
                continue
            verified = False
            broken_event_id = event.event_id
            reason = item_reason
            break

        state = await asyncio.to_thread(self._current_state_sync)

        return AuditVerifyResponse(
            verified=verified,
            checked_events=len(events),
            first_event_id=events[0].event_id,
            last_event_id=events[-1].event_id,
            broken_event_id=broken_event_id,
            reason=reason,
            state_tx_id=state["tx_id"],
            state_tx_hash=state["tx_hash"],
        )

    async def _ensure_schema(self) -> None:
        if self._schema_ready:
            return

        async with self._schema_lock:
            if self._schema_ready:
                return
            await asyncio.to_thread(self._ensure_schema_sync)
            self._schema_ready = True

    def _with_session(self, callback: Callable[[Any], Any]) -> Any:
        try:
            from immudb.client import ImmudbClient as RawImmudbClient
        except ImportError as exc:
            raise ImmudbOperationError(
                "immudb-py is not installed; install dependencies before using audit APIs"
            ) from exc

        target = f"{self.host}:{self.port}"
        client = RawImmudbClient(target)
        try:
            client.openSession(
                self.username.encode("utf-8"),
                self.password.encode("utf-8"),
                self.database.encode("utf-8"),
            )
            return callback(client)
        except Exception as exc:  # pragma: no cover - depends on immudb runtime
            raise ImmudbOperationError(str(exc)) from exc
        finally:
            try:
                client.closeSession()
            except Exception:
                pass

    def _ensure_schema_sync(self) -> None:
        create_stmt = """
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER AUTO_INCREMENT,
            event_id VARCHAR[64],
            ts_ms INTEGER,
            actor_type VARCHAR[16],
            actor_id VARCHAR[255],
            action_type VARCHAR[128],
            resource_type VARCHAR[64],
            resource_id VARCHAR[255],
            decision VARCHAR[16],
            reason_code VARCHAR[128],
            input_hash VARCHAR[128],
            output_hash VARCHAR[128],
            prev_hash VARCHAR[128],
            chain_hash VARCHAR[128],
            signature VARCHAR[512],
            user_id VARCHAR[255],
            room_id VARCHAR[255],
            event_payload JSON,
            PRIMARY KEY id
        )
        """

        def operation(client: Any) -> None:
            client.sqlExec(create_stmt)
            self._ensure_required_columns(client)

        self._with_session(operation)

    def _ensure_required_columns(self, client: Any) -> None:
        required_columns: dict[str, str] = {
            "event_id": "VARCHAR[64]",
            "ts_ms": "INTEGER",
            "actor_type": "VARCHAR[16]",
            "actor_id": "VARCHAR[255]",
            "action_type": "VARCHAR[128]",
            "resource_type": "VARCHAR[64]",
            "resource_id": "VARCHAR[255]",
            "decision": "VARCHAR[16]",
            "reason_code": "VARCHAR[128]",
            "input_hash": "VARCHAR[128]",
            "output_hash": "VARCHAR[128]",
            "prev_hash": "VARCHAR[128]",
            "chain_hash": "VARCHAR[128]",
            "signature": "VARCHAR[512]",
            "user_id": "VARCHAR[255]",
            "room_id": "VARCHAR[255]",
            "event_payload": "JSON",
        }
        rows = list(client.sqlQuery("SELECT * FROM COLUMNS('audit_events')"))
        existing_columns = {str(row[1]) for row in rows}

        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue
            client.sqlExec(f"ALTER TABLE audit_events ADD COLUMN {column_name} {column_type}")

    def _insert_event_sync(self, event: AuditEvent) -> int | None:
        insert_stmt = """
        INSERT INTO audit_events (
            event_id, ts_ms, actor_type, actor_id, action_type,
            resource_type, resource_id, decision, reason_code,
            input_hash, output_hash, prev_hash, chain_hash, signature,
            user_id, room_id, event_payload
        ) VALUES (
            @event_id, @ts_ms, @actor_type, @actor_id, @action_type,
            @resource_type, @resource_id, @decision, @reason_code,
            @input_hash, @output_hash, @prev_hash, @chain_hash, @signature,
            @user_id, @room_id, @event_payload
        )
        """

        params: dict[str, Any] = {
            "event_id": event.event_id,
            "ts_ms": event.ts_ms,
            "actor_type": event.actor_type.value,
            "actor_id": event.actor_id,
            "action_type": event.action_type,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "decision": event.decision.value,
            "reason_code": event.reason_code or "",
            "input_hash": event.input_hash,
            "output_hash": event.output_hash,
            "prev_hash": event.prev_hash or "",
            "chain_hash": event.chain_hash,
            "signature": event.signature or "",
            "user_id": event.user_id or "",
            "room_id": event.room_id or "",
            "event_payload": json.dumps(
                {
                    "metadata": event.metadata,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        }

        def operation(client: Any) -> int | None:
            result = client.sqlExec(insert_stmt, params)
            txs = getattr(result, "txs", None)
            if not txs:
                return None
            header = getattr(txs[0], "header", None)
            if header is None:
                return None
            return int(getattr(header, "id", 0))

        return self._with_session(operation)

    def _query_events_sync(self, query: AuditQuery, descending: bool) -> list[tuple[Any, ...]]:
        where_clause, params = self._build_where_clause(query)
        order_direction = "DESC" if descending else "ASC"
        sql = f"""
        SELECT
            id, event_id, ts_ms, actor_type, actor_id, action_type,
            resource_type, resource_id, decision, reason_code,
            input_hash, output_hash, prev_hash, chain_hash, signature,
            user_id, room_id, event_payload
        FROM audit_events
        {where_clause}
        ORDER BY id {order_direction}
        LIMIT @limit
        """
        params["limit"] = query.limit

        def operation(client: Any) -> list[tuple[Any, ...]]:
            return list(client.sqlQuery(sql, params))

        return self._with_session(operation)

    def _get_latest_chain_hash_sync(self) -> str | None:
        def operation(client: Any) -> str | None:
            rows = client.sqlQuery(
                "SELECT chain_hash FROM audit_events "
                f"WHERE {self._valid_event_predicate} ORDER BY id DESC LIMIT 1"
            )
            if not rows:
                return None
            chain_hash = rows[0][0]
            if chain_hash in ("", None):
                return None
            return str(chain_hash)

        return self._with_session(operation)

    def _get_prev_hash_before_id_sync(self, event_row_id: int) -> str | None:
        stmt = (
            "SELECT chain_hash FROM audit_events "
            f"WHERE id < @event_row_id AND {self._valid_event_predicate} "
            "ORDER BY id DESC LIMIT 1"
        )

        def operation(client: Any) -> str | None:
            rows = client.sqlQuery(stmt, {"event_row_id": event_row_id})
            if not rows:
                return None
            value = rows[0][0]
            if value in ("", None):
                return None
            return str(value)

        return self._with_session(operation)

    def _current_state_sync(self) -> dict[str, Any]:
        def operation(client: Any) -> dict[str, Any]:
            state = client.currentState()
            tx_hash = getattr(state, "txHash", b"")
            return {
                "tx_id": int(getattr(state, "txId", 0)),
                "tx_hash": tx_hash.hex() if isinstance(tx_hash, bytes) else "",
            }

        return self._with_session(operation)

    def _build_where_clause(self, query: AuditQuery) -> tuple[str, dict[str, Any]]:
        clauses: list[str] = [self._valid_event_predicate]
        params: dict[str, Any] = {}

        if query.actor_id is not None:
            clauses.append("actor_id = @actor_id")
            params["actor_id"] = query.actor_id

        if query.user_id is not None:
            clauses.append("user_id = @user_id")
            params["user_id"] = query.user_id

        if query.room_id is not None:
            clauses.append("room_id = @room_id")
            params["room_id"] = query.room_id

        if query.action_type is not None:
            clauses.append("action_type = @action_type")
            params["action_type"] = query.action_type

        if query.decision is not None:
            clauses.append("decision = @decision")
            params["decision"] = query.decision.value

        if query.start_ts_ms is not None:
            clauses.append("ts_ms >= @start_ts_ms")
            params["start_ts_ms"] = query.start_ts_ms

        if query.end_ts_ms is not None:
            clauses.append("ts_ms <= @end_ts_ms")
            params["end_ts_ms"] = query.end_ts_ms

        return f"WHERE {' AND '.join(clauses)}", params

    def _row_to_event(self, row: tuple[Any, ...]) -> AuditEvent:
        payload_raw = row[17]
        metadata: dict[str, Any] = {}
        if isinstance(payload_raw, str) and payload_raw:
            try:
                payload_obj = json.loads(payload_raw)
                if isinstance(payload_obj, dict):
                    metadata_obj = payload_obj.get("metadata", {})
                    if isinstance(metadata_obj, dict):
                        metadata = metadata_obj
            except json.JSONDecodeError:
                metadata = {}

        prev_hash_raw = row[12]
        signature_raw = row[14]
        reason_code_raw = row[9]
        user_id_raw = row[15]
        room_id_raw = row[16]

        ts_ms = int(row[2])
        ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

        return AuditEvent(
            event_id=str(row[1]),
            ts=ts,
            ts_ms=ts_ms,
            actor_type=str(row[3]),
            actor_id=str(row[4]),
            action_type=str(row[5]),
            resource_type=str(row[6]),
            resource_id=str(row[7]),
            decision=str(row[8]),
            reason_code=str(reason_code_raw) if reason_code_raw else None,
            input_hash=str(row[10]),
            output_hash=str(row[11]),
            prev_hash=str(prev_hash_raw) if prev_hash_raw else None,
            chain_hash=str(row[13]),
            signature=str(signature_raw) if signature_raw else None,
            user_id=str(user_id_raw) if user_id_raw else None,
            room_id=str(room_id_raw) if room_id_raw else None,
            metadata=metadata,
        )
