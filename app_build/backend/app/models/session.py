import time
from typing import Optional, Dict
from pydantic import BaseModel, Field

class CallSession(BaseModel):
    """
    Short-TTL Call Session Object
    Contains: phone_hash, last_answer_text, last_answer_tier, call_active
    """
    phone_hash: str
    last_answer_text: str = ""
    last_answer_tier: str = "STANDARD"  # Tier: SIMPLE | STANDARD | DETAILED
    call_active: bool = True
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def touch(self):
        self.updated_at = time.time()

    def is_expired(self, ttl_seconds: int = 900) -> bool:
        return (time.time() - self.updated_at) > ttl_seconds
