"""Shared dependency accessors for FastAPI routes."""

from __future__ import annotations

from typing import cast

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.audit.immudb_client import ImmudbClient
from app.bridge.telegram_client import TelegramBridgeClient
from app.matrix.client import MatrixClient, MatrixClientError
from app.policy.opa_client import OPAClient


def get_opa_client(request: Request) -> OPAClient:
    return cast(OPAClient, request.app.state.opa_client)


def get_immudb_client(request: Request) -> ImmudbClient:
    return cast(ImmudbClient, request.app.state.immudb_client)


def get_telegram_bridge_client(request: Request) -> TelegramBridgeClient:
    return cast(TelegramBridgeClient, request.app.state.telegram_bridge_client)


class AuthenticatedUser(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    access_token: str = Field(min_length=1)


_bearer_scheme = HTTPBearer(auto_error=False)


async def get_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="invalid_auth_scheme")

    access_token = credentials.credentials.strip()
    if access_token == "":
        raise HTTPException(status_code=401, detail="missing_bearer_token")

    matrix_client = cast(MatrixClient, request.app.state.matrix_client)
    try:
        whoami = await matrix_client.whoami(access_token=access_token)
    except MatrixClientError as exc:
        raise HTTPException(status_code=401, detail=f"invalid_access_token: {exc}") from exc

    user_id = whoami.get("user_id")
    if not isinstance(user_id, str) or user_id == "":
        raise HTTPException(status_code=401, detail="invalid_whoami_response")

    return AuthenticatedUser(user_id=user_id, access_token=access_token)
