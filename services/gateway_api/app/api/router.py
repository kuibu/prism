from fastapi import APIRouter

from app.api import agent, agents, audit, bridges, health, matrix, policy

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(audit.router)
api_router.include_router(policy.router)
api_router.include_router(agent.router)
api_router.include_router(agents.router)
api_router.include_router(matrix.router)
api_router.include_router(bridges.router)
