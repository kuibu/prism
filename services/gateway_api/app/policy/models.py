from datetime import datetime

from pydantic import BaseModel, Field


class PolicyDecisionInput(BaseModel):
    agent_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    room_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    ts: datetime


class PolicyDecision(BaseModel):
    allow: bool
    reason: str
