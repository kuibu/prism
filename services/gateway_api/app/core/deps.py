"""Shared dependency accessors for FastAPI routes."""

from fastapi import Request

from app.audit.immudb_client import ImmudbClient
from app.policy.opa_client import OPAClient


def get_opa_client(request: Request) -> OPAClient:
    return request.app.state.opa_client


def get_immudb_client(request: Request) -> ImmudbClient:
    return request.app.state.immudb_client
