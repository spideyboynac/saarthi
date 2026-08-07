import hashlib
from typing import Dict, Optional
from app.models.session import CallSession
from app.config import settings

class SessionService:
    def __init__(self):
        self._sessions: Dict[str, CallSession] = {}

    def get_or_create_session(self, phone_identifier: str) -> CallSession:
        phone_hash = hashlib.sha256(phone_identifier.encode('utf-8')).hexdigest()[:16]
        
        session = self._sessions.get(phone_hash)
        if not session or session.is_expired(settings.SESSION_TTL_SECONDS):
            session = CallSession(phone_hash=phone_hash, last_answer_text="", last_answer_tier="STANDARD", call_active=True)
            self._sessions[phone_hash] = session
        else:
            session.touch()
        
        return session

    def get_session_by_hash(self, phone_hash: str) -> Optional[CallSession]:
        session = self._sessions.get(phone_hash)
        if session and not session.is_expired(settings.SESSION_TTL_SECONDS):
            session.touch()
            return session
        return None

    def update_session(self, phone_hash: str, last_answer_text: str, last_answer_tier: str, call_active: bool = True) -> CallSession:
        session = self.get_session_by_hash(phone_hash)
        if not session:
            session = CallSession(phone_hash=phone_hash, last_answer_text=last_answer_text, last_answer_tier=last_answer_tier, call_active=call_active)
            self._sessions[phone_hash] = session
        else:
            session.last_answer_text = last_answer_text
            session.last_answer_tier = last_answer_tier
            session.call_active = call_active
            session.touch()
        return session

session_service = SessionService()
