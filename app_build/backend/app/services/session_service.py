import hashlib
from typing import Dict, Optional, Tuple
from app.models.session import CallSession, UserProfile
from app.config import settings

class SessionService:
    def __init__(self):
        self._sessions: Dict[str, CallSession] = {}
        self._profiles: Dict[str, UserProfile] = {}

    def get_phone_hash(self, phone_identifier: str) -> str:
        # Enforce SHA-256 phone hashing before any profile/session write/read
        if len(phone_identifier) == 16 and not phone_identifier.startswith("+") and not phone_identifier.startswith("demo"):
            return phone_identifier
        return hashlib.sha256(phone_identifier.encode('utf-8')).hexdigest()[:16]

    def get_or_create_profile(self, phone_identifier: str) -> UserProfile:
        phone_hash = self.get_phone_hash(phone_identifier)
        profile = self._profiles.get(phone_hash)
        if not profile:
            profile = UserProfile(phone_hash=phone_hash, current_tier="STANDARD", first_time_caller=True, total_calls=1)
            self._profiles[phone_hash] = profile
        else:
            profile.touch()
        return profile

    def mark_onboarding_completed(self, phone_identifier: str) -> UserProfile:
        profile = self.get_or_create_profile(phone_identifier)
        profile.first_time_caller = False
        profile.touch()
        return profile

    def degrade_tier(self, phone_identifier: str) -> str:
        """Key 4 press: drops literacy tier by one step, increments reexplain_count, resets clean_calls_count."""
        profile = self.get_or_create_profile(phone_identifier)
        profile.reexplain_count += 1
        profile.clean_calls_count = 0
        if profile.current_tier == "DETAILED":
            profile.current_tier = "STANDARD"
        elif profile.current_tier == "STANDARD":
            profile.current_tier = "SIMPLE"
        profile.touch()
        return profile.current_tier

    def record_clean_call(self, phone_identifier: str) -> str:
        """Increments clean call count; slowly creeps literacy tier back up after 3 clean calls."""
        profile = self.get_or_create_profile(phone_identifier)
        profile.clean_calls_count += 1
        profile.total_calls += 1
        if profile.clean_calls_count >= 3:
            if profile.current_tier == "SIMPLE":
                profile.current_tier = "STANDARD"
            elif profile.current_tier == "STANDARD":
                profile.current_tier = "DETAILED"
            profile.clean_calls_count = 0
        profile.touch()
        return profile.current_tier

    def get_or_create_session(self, phone_identifier: str) -> CallSession:
        phone_hash = self.get_phone_hash(phone_identifier)
        profile = self.get_or_create_profile(phone_identifier)
        
        session = self._sessions.get(phone_hash)
        if not session or session.is_expired(settings.SESSION_TTL_SECONDS):
            session = CallSession(
                phone_hash=phone_hash,
                last_answer_text="",
                last_answer_tier=profile.current_tier,
                call_active=True
            )
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

    def update_session(self, phone_hash: str, last_answer_text: str, last_answer_tier: str, call_active: bool = True, last_question: str = "", last_sources: list = None) -> CallSession:
        session = self.get_session_by_hash(phone_hash)
        if last_sources is None:
            last_sources = []
        if not session:
            session = CallSession(
                phone_hash=phone_hash,
                last_question=last_question,
                last_sources=last_sources,
                last_answer_text=last_answer_text,
                last_answer_tier=last_answer_tier,
                call_active=call_active
            )
            self._sessions[phone_hash] = session
        else:
            if last_question:
                session.last_question = last_question
            if last_sources:
                session.last_sources = last_sources
            session.last_answer_text = last_answer_text
            session.last_answer_tier = last_answer_tier
            session.call_active = call_active
            session.touch()
        return session

session_service = SessionService()
