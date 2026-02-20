from fastapi import APIRouter

from app.api import agent, audit, health, matrix, policy

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(audit.router)
api_router.include_router(policy.router)
api_router.include_router(agent.router)
api_router.include_router(matrix.router)
