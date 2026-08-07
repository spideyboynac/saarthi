import hashlib
import time
from typing import Dict, Optional
from app.models.session import CallSession, UserProfile
from app.config import settings


class SessionService:
    """
    Short-TTL call session and persistent user profile store.

    Architecture contract (v3.0 spec §2.2):
      call_session TTL = 15 minutes (SESSION_TTL_SECONDS in config)
      Sessions are in-memory only — purged on expiry or explicit termination.
      phone_hash is always SHA-256[:16] — raw phone numbers are NEVER stored.
    """

    def __init__(self):
        self._sessions: Dict[str, CallSession] = {}
        self._profiles: Dict[str, UserProfile] = {}

    # ------------------------------------------------------------------
    # Identity helpers
    # ------------------------------------------------------------------

    def get_phone_hash(self, phone_identifier: str) -> str:
        """
        Returns the canonical 16-char hex phone_hash for any identifier.
        If the identifier is already a 16-char hex hash, returns it unchanged.
        All other strings (raw phone numbers, WebSocket session IDs, etc.)
        are SHA-256 hashed to produce a privacy-safe, stable key.
        """
        if (
            len(phone_identifier) == 16
            and not phone_identifier.startswith("+")
            and not phone_identifier.startswith("demo")
        ):
            return phone_identifier
        return hashlib.sha256(phone_identifier.encode("utf-8")).hexdigest()[:16]

    # ------------------------------------------------------------------
    # User profile management (persistent, in-memory for hackathon build)
    # ------------------------------------------------------------------

    def get_or_create_profile(self, phone_identifier: str) -> UserProfile:
        phone_hash = self.get_phone_hash(phone_identifier)
        profile = self._profiles.get(phone_hash)
        if not profile:
            profile = UserProfile(
                phone_hash=phone_hash,
                current_tier="STANDARD",
                first_time_caller=True,
                total_calls=1,
            )
            self._profiles[phone_hash] = profile
        else:
            profile.touch()
        return profile

    def mark_onboarding_completed(self, phone_identifier: str) -> UserProfile:
        """Called once per new caller after the disclaimer plays."""
        profile = self.get_or_create_profile(phone_identifier)
        profile.first_time_caller = False
        profile.touch()
        return profile

    def degrade_tier(self, phone_identifier: str) -> str:
        """
        Action 4 (Simplify) handler: drops literacy tier one step.
        Increments reexplain_count and resets clean_calls_count.
        RAG bypass is the caller's responsibility — this method only manages state.
        """
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
        """
        Called at the end of a call with no key-4 presses.
        Slowly creeps literacy tier back up after 3 consecutive clean calls.
        """
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

    # ------------------------------------------------------------------
    # Call session management (short-TTL, per-call in-memory)
    # ------------------------------------------------------------------

    def get_or_create_session(self, phone_identifier: str) -> CallSession:
        """
        Returns the active session for the caller, or creates a fresh one
        if none exists or the existing session has exceeded SESSION_TTL_SECONDS.
        Expired sessions are replaced — never returned with stale state.
        """
        phone_hash = self.get_phone_hash(phone_identifier)
        profile = self.get_or_create_profile(phone_identifier)

        session = self._sessions.get(phone_hash)
        if not session or session.is_expired(settings.SESSION_TTL_SECONDS):
            session = CallSession(
                phone_hash=phone_hash,
                last_answer_text="",
                last_answer_tier=profile.current_tier,
                call_active=True,
            )
            self._sessions[phone_hash] = session
        else:
            session.touch()

        return session

    def get_session_by_hash(self, phone_hash: str) -> Optional[CallSession]:
        """Returns the session if it exists and has not expired, else None."""
        session = self._sessions.get(phone_hash)
        if session and not session.is_expired(settings.SESSION_TTL_SECONDS):
            session.touch()
            return session
        return None

    def update_session(
        self,
        phone_hash: str,
        last_answer_text: str,
        last_answer_tier: str,
        call_active: bool = True,
        last_question: str = "",
        last_sources: list = None,
    ) -> CallSession:
        """
        Writes the result of a completed pipeline run into the call session.
        Called after every Action 1/2 (New Question) response is generated.
        Actions 3, 4, 5 also call this to keep last_answer_text current.
        """
        if last_sources is None:
            last_sources = []
        session = self.get_session_by_hash(phone_hash)
        if not session:
            session = CallSession(
                phone_hash=phone_hash,
                last_question=last_question,
                last_sources=last_sources,
                last_answer_text=last_answer_text,
                last_answer_tier=last_answer_tier,
                call_active=call_active,
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

    def terminate_session(self, phone_hash: str) -> None:
        """
        Explicitly terminates an active call session (Action 6 / call hangup).
        Sets call_active=False and backdates updated_at so the next
        get_or_create_session will spawn a clean session.
        """
        session = self._sessions.get(phone_hash)
        if session:
            session.call_active = False
            # Backdate so the session is treated as expired immediately
            session.updated_at = time.time() - settings.SESSION_TTL_SECONDS - 1

    def purge_expired_sessions(self) -> int:
        """
        Removes all expired sessions from the in-memory store.
        Call periodically (e.g., from a FastAPI background task or lifespan hook)
        to prevent unbounded memory growth in long-running deployments.
        Returns the count of sessions purged.
        """
        expired_keys = [
            k
            for k, s in self._sessions.items()
            if s.is_expired(settings.SESSION_TTL_SECONDS)
        ]
        for k in expired_keys:
            del self._sessions[k]
        return len(expired_keys)


session_service = SessionService()
