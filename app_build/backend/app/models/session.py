import time
from typing import Optional, Dict
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    """
    Persistent User Profile Object
    Keyed by phone_hash (SHA-256 hashed phone number)
    Contains: phone_hash, current_tier, reexplain_count, total_calls, clean_calls_count, first_time_caller, last_updated
    """
    phone_hash: str
    current_tier: str = "STANDARD"  # Tier: SIMPLE | STANDARD | DETAILED
    reexplain_count: int = 0
    total_calls: int = 0
    clean_calls_count: int = 0
    first_time_caller: bool = True
    last_updated: float = Field(default_factory=time.time)

    def touch(self):
        self.last_updated = time.time()

class CallSession(BaseModel):
    """
    Short-TTL Call Session Object (Per-Call Memory)
    Contains: phone_hash, last_question, last_sources, last_answer_text, last_answer_tier, call_active
    """
    phone_hash: str
    last_question: Optional[str] = ""
    last_sources: list = Field(default_factory=list)
    last_answer_text: str = ""
    last_answer_tier: str = "STANDARD"  # Tier: SIMPLE | STANDARD | DETAILED
    call_active: bool = True
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def touch(self):
        self.updated_at = time.time()

    def is_expired(self, ttl_seconds: int = 900) -> bool:
        return (time.time() - self.updated_at) > ttl_seconds
