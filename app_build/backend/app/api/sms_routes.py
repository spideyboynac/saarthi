import os
from fastapi import APIRouter, Request, Response
try:
    from twilio.twiml.messaging_response import MessagingResponse
    HAS_TWILIO = True
except ImportError:
    HAS_TWILIO = False

from app.services.action_handler import action_handler_engine
from app.services.session_service import session_service

router = APIRouter(prefix="/twilio", tags=["Twilio SMS"])

# Maximum characters before truncation + hint
SMS_MAX_CHARS = 800
SMS_TRUNCATE_HINT = "\n\n[Reply FULL to get the complete answer]"

HELP_TEXT = (
    "Nyaya Dhwani Legal Assistant / Nyaya Dhwani Kanooni Sahayak\n\n"
    "English Commands:\n"
    "  ASK <your question> — Get legal advice\n"
    "  REPEAT — Replay last answer\n"
    "  SIMPLIFY — Simpler explanation\n"
    "  FOLLOWUP — Suggested questions\n"
    "  DLSA — Connect to legal aid\n"
    "  STOP — End session\n\n"
    "Hindi Commands:\n"
    "  ASK <apna sawal> — Kanooni salah lein\n"
    "  SIMPLIFY — Aasan bhasha mein samjhein\n\n"
    "Disclaimer: AI legal assistant, not a lawyer / AI kanooni sahayak, vakil nahi."
)

DISCLAIMER = (
    "Welcome to Nyaya Dhwani / Nyaya Dhwani mein aapka swagat hai.\n"
    "Disclaimer: I am an AI legal literacy assistant, not a lawyer. / Yeh ek AI kanooni sahayak hai, vakil nahi.\n\n"
)


def _truncate(text: str) -> str:
    """Truncate answer to SMS_MAX_CHARS and append hint if needed."""
    if len(text) <= SMS_MAX_CHARS:
        return text
    return text[:SMS_MAX_CHARS - len(SMS_TRUNCATE_HINT)] + SMS_TRUNCATE_HINT


def _send_sms_via_client(to_phone: str, body: str):
    """Sends SMS actively via Twilio REST API client (guarantees delivery if TwiML fails)."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_phone = os.getenv("TWILIO_PHONE_NUMBER")

    if account_sid and auth_token and from_phone:
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            msg = client.messages.create(
                body=body,
                from_=from_phone,
                to=to_phone
            )
            print(f"    [SMS REST CLIENT] Outbound SMS dispatched to {to_phone} | SID: {msg.sid}")
        except Exception as err:
            print(f"    [SMS REST CLIENT] Failed to send SMS via REST Client: {err}")


def _twiml_response(body: str, to_phone: str = None) -> str:
    """Generate a raw TwiML MessagingResponse XML string and trigger REST dispatch if phone provided."""
    if to_phone:
        _send_sms_via_client(to_phone, body)

    if HAS_TWILIO:
        resp = MessagingResponse()
        resp.message(body)
        return str(resp)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Message><Body>{body}</Body></Message></Response>'
    )


@router.post("/sms")
async def twilio_sms_webhook(request: Request):
    """
    Twilio SMS Webhook — POST /api/v1/twilio/sms

    Keyword command interface that mirrors the 6-Action IVR voice map.
    Session state is shared with voice via the same session_service hash.
    """
    form = await request.form()
    raw_body: str = (form.get("Body") or "").strip()
    from_number: str = form.get("From", "sms-unknown")

    # Shared session/profile (same hash as voice — cross-channel memory)
    profile = session_service.get_or_create_profile(from_number)
    first_time = profile.first_time_caller

    # Mark onboarding done after first message
    if first_time:
        session_service.mark_onboarding_completed(from_number)

    cmd = raw_body.upper()

    # ----------------------------------------------------------------
    # HELP / empty -> return menu
    # ----------------------------------------------------------------
    if not raw_body or cmd == "HELP":
        prefix = DISCLAIMER if first_time else ""
        return Response(
            content=_twiml_response(prefix + HELP_TEXT, to_phone=from_number),
            media_type="application/xml"
        )

    # ----------------------------------------------------------------
    # DLSA -> Human handoff
    # ----------------------------------------------------------------
    if cmd == "DLSA":
        session = session_service.get_or_create_session(from_number)
        summary = (session.last_answer_text or "No query on record.")[:200]
        reply = (
            "Connecting you to the District Legal Services Authority (DLSA).\n\n"
            f"Your case summary: {summary}\n\n"
            "Call DLSA toll-free: 1800-110-005"
        )
        return Response(content=_twiml_response(reply, to_phone=from_number), media_type="application/xml")

    # ----------------------------------------------------------------
    # STOP -> terminate session
    # ----------------------------------------------------------------
    if cmd == "STOP":
        session = session_service.get_or_create_session(from_number)
        session_service.terminate_session(session.phone_hash)
        return Response(
            content=_twiml_response("Session ended. Reply ASK <question> to start a new query.", to_phone=from_number),
            media_type="application/xml"
        )

    # ----------------------------------------------------------------
    # REPEAT / SIMPLIFY / FOLLOWUP -> RAG Bypass actions
    # ----------------------------------------------------------------
    if cmd in ("REPEAT", "SIMPLIFY", "FOLLOWUP"):
        action_map = {"REPEAT": 3, "SIMPLIFY": 4, "FOLLOWUP": 5}
        action_code = action_map[cmd]
        try:
            res = action_handler_engine.process_action(
                phone_identifier=from_number,
                action_code=action_code,
                payload=None
            )
            reply = _truncate(res.answer_text)
        except Exception as e:
            reply = f"Error processing {cmd}: {str(e)[:200]}"
        prefix = DISCLAIMER if first_time else ""
        return Response(content=_twiml_response(prefix + reply, to_phone=from_number), media_type="application/xml")

    # ----------------------------------------------------------------
    # ASK <question> -> Full Dual-RAG + Ollama pipeline (Action 2)
    # ----------------------------------------------------------------
    if cmd.startswith("ASK "):
        question = raw_body[4:].strip()  # preserve original casing
        if not question:
            return Response(
                content=_twiml_response(
                    "Please include your question. Example:\nASK What are my rights if arrested?",
                    to_phone=from_number
                ),
                media_type="application/xml"
            )
        try:
            res = action_handler_engine.process_action(
                phone_identifier=from_number,
                action_code=2,
                payload=question
            )
            answer = _truncate(res.answer_text)
            sources_line = ""
            if res.sources:
                sources_line = f"\n\nSources: {', '.join(res.sources[:2])}"
            reply = f"{answer}{sources_line}"
        except Exception as e:
            reply = f"Error: {str(e)[:300]}"
        prefix = DISCLAIMER if first_time else ""
        return Response(content=_twiml_response(prefix + reply, to_phone=from_number), media_type="application/xml")

    # ----------------------------------------------------------------
    # FULL -> Return complete last answer without truncation
    # ----------------------------------------------------------------
    if cmd == "FULL":
        session = session_service.get_or_create_session(from_number)
        last = session.last_answer_text
        if not last:
            reply = "No previous answer found. Reply ASK <question> first."
        else:
            reply = last  # Twilio auto-concatenates multi-segment SMS
        return Response(content=_twiml_response(reply, to_phone=from_number), media_type="application/xml")

    # ----------------------------------------------------------------
    # Unknown command -> show help
    # ----------------------------------------------------------------
    prefix = DISCLAIMER if first_time else ""
    return Response(
        content=_twiml_response(prefix + f'Unknown command "{raw_body[:30]}". ' + HELP_TEXT, to_phone=from_number),
        media_type="application/xml"
    )
