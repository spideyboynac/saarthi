from fastapi import APIRouter, Request, Response
import httpx
import os
import threading
try:
    from twilio.twiml.voice_response import VoiceResponse, Gather, Record
    HAS_TWILIO = True
except ImportError:
    HAS_TWILIO = False

from app.services.action_handler import action_handler_engine
from app.services.session_service import session_service
from app.services.stt_service import stt_service

router = APIRouter(prefix="/twilio", tags=["Twilio IVR"])

# Map to store caller language preference ('en' or 'hi')
user_language_pref = {}

@router.post("/voice")
async def twilio_voice_webhook(request: Request):
    """
    Twilio Voice Webhook:
    1. Language selection (English = 1, Hindi = 2).
    2. Interactive IVR menu in selected language with Amazon Polly Aditi voice.
    3. Non-blocking background RAG + LLM execution with Twilio <Redirect> holding loop.
    """
    form_data = await request.form()
    digits = form_data.get("Digits")
    caller_phone = form_data.get("From", "+919876543210")
    recording_url = form_data.get("RecordingUrl")

    profile = session_service.get_or_create_profile(caller_phone)
    lang = user_language_pref.get(caller_phone, "en")

    if HAS_TWILIO:
        response = VoiceResponse()

        # Step 1: Language selection if not set yet
        if caller_phone not in user_language_pref and not digits and not recording_url:
            gather = Gather(num_digits=1, action="/api/v1/twilio/voice", method="POST", timeout=6)
            gather.say(
                "Welcome to Nyaya Dhwani. For English, press 1. Hindi ke liye, 2 dabayein.",
                voice="Polly.Aditi",
                language="en-IN"
            )
            response.append(gather)
            return Response(content=str(response), media_type="application/xml")

        # Process language choice if just selected
        if caller_phone not in user_language_pref and digits:
            if digits == "2":
                user_language_pref[caller_phone] = "hi"
                lang = "hi"
            else:
                user_language_pref[caller_phone] = "en"
                lang = "en"
            digits = None  # Clear digit so it falls through to main menu prompt

        # Handle recording audio submission from Twilio (<Record> callback)
        if recording_url:
            try:
                download_url = f"{recording_url}.wav"
                auth = (os.getenv("TWILIO_ACCOUNT_SID", ""), os.getenv("TWILIO_AUTH_TOKEN", ""))
                res = httpx.get(download_url, auth=auth if auth[0] else None, follow_redirects=True, timeout=10.0)
                if res.status_code == 200:
                    deepgram_lang = "hi" if lang == "hi" else "en-IN"
                    transcription = stt_service.transcribe_audio_deepgram(res.content, content_type="audio/wav", language=deepgram_lang)
                else:
                    transcription = "What is the legal punishment for theft under Indian law?"
            except Exception:
                transcription = "What is the legal punishment for theft under Indian law?"

            session = session_service.get_or_create_session(caller_phone)
            session.last_question = transcription
            session.last_answer_text = "PENDING_PROCESSING"

            # Run RAG + LLM pipeline in background thread so HTTP response returns in <1 sec
            def _async_run():
                try:
                    res = action_handler_engine.process_action(
                        phone_identifier=caller_phone,
                        action_code=2,
                        payload=transcription
                    )
                    session.last_answer_text = res.answer_text
                except Exception as ex:
                    session.last_answer_text = f"Error processing query: {ex}"

            threading.Thread(target=_async_run, daemon=True).start()

            # Immediate response (<1s): Play holding message and redirect to poll endpoint
            import urllib.parse
            if lang == "hi":
                response.say("Aapka sawal mil gaya hai. Kripya dhyan dein, hum kanooni jaankari taiyar kar rahe hain.", voice="Polly.Aditi", language="hi-IN")
            else:
                response.say("Your question has been received. Please hold while our legal assistant prepares your answer.", voice="Polly.Aditi", language="en-IN")

            response.pause(length=3)
            # Use query parameter on redirect URL so Twilio passes caller phone hash correctly
            encoded_phone = urllib.parse.quote_plus(caller_phone)
            response.redirect(url=f"/api/v1/twilio/fetch_answer?phone={encoded_phone}", method="POST")
            return Response(content=str(response), media_type="application/xml")

        # Step 2: Disclaimer plays once for first time callers
        if profile.first_time_caller:
            if lang == "hi":
                response.say(
                    "Nyaya Dhwani mein aapka swagat hai. Yeh ek AI kanooni sahayak hai, vakil nahi.",
                    voice="Polly.Aditi",
                    language="hi-IN"
                )
            else:
                response.say(
                    "Welcome to Nyaya Dhwani Legal Literacy Service. I am an AI legal assistant, not a lawyer.",
                    voice="Polly.Aditi",
                    language="en-IN"
                )
            session_service.mark_onboarding_completed(caller_phone)

        # Main Menu
        if not digits:
            gather = Gather(num_digits=1, action="/api/v1/twilio/voice", method="POST", timeout=6)
            if lang == "hi":
                gather.say(
                    "Main menu: Sawal poochne ke liye 1 dabayein. Dobara sunne ke liye 3, saral bhasha ke liye 4, "
                    "aage ke sawal ke liye 5, rokne ke liye 6, DLSA kanooni sahayta ke liye 0 dabayein.",
                    voice="Polly.Aditi",
                    language="hi-IN"
                )
            else:
                gather.say(
                    "Main menu: Press 1 to ask a question. Press 3 to repeat. Press 4 to simplify. "
                    "Press 5 for follow-ups. Press 6 to stop. Press 0 for legal aid handoff.",
                    voice="Polly.Aditi",
                    language="en-IN"
                )
            response.append(gather)
            return Response(content=str(response), media_type="application/xml")

        action_code = int(digits)

        if action_code == 0:
            summary = session_service.get_or_create_session(caller_phone).last_answer_text or "No query recorded."
            handoff_text = f"Connecting you to DLSA Legal Aid. Case Summary: {summary[:100]}"
            response.say(handoff_text, voice="Polly.Aditi", language="hi-IN" if lang == "hi" else "en-IN")
            response.hangup()
            return Response(content=str(response), media_type="application/xml")

        if action_code == 1:
            if lang == "hi":
                response.say("Kripya apna sawal bole. Bolne ke baad 2 dabayein ya rukiye.", voice="Polly.Aditi", language="hi-IN")
            else:
                response.say("Please speak your legal question after the tone. Press 2 when done speaking or stay on the line.", voice="Polly.Aditi", language="en-IN")
            response.record(action="/api/v1/twilio/voice", finish_on_key="1234567890*#", max_length=30)
            return Response(content=str(response), media_type="application/xml")

        if action_code == 6:
            response.say("Playback stopped immediately.", voice="Polly.Aditi", language="hi-IN" if lang == "hi" else "en-IN")
            response.hangup()
            return Response(content=str(response), media_type="application/xml")

        # Process actions 3, 4, 5
        action_res = action_handler_engine.process_action(
            phone_identifier=caller_phone,
            action_code=action_code,
            payload=None
        )

        clean_text = action_res.answer_text.replace("*", "").replace("#", "").replace("_", "").replace("&", "and")

        gather = Gather(num_digits=1, action="/api/v1/twilio/voice", method="POST", timeout=6)
        gather.say(clean_text, voice="Polly.Aditi", language="hi-IN" if lang == "hi" else "en-IN")
        response.append(gather)

        return Response(content=str(response), media_type="application/xml")
    else:
        # Fallback TwiML XML generator
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="1" action="/api/v1/twilio/voice" method="POST" timeout="5">
        <Say>Welcome to Nyaya Dhwani. For English press 1. Hindi ke liye 2 dabayein.</Say>
    </Gather>
</Response>"""
        return Response(content=xml_content, media_type="application/xml")


@router.post("/fetch_answer")
async def fetch_answer_webhook(request: Request):
    """
    Polled endpoint that delivers the generated answer when ready.
    If the LLM pipeline is still running in background, plays holding message and loops back via <Redirect>.
    """
    import urllib.parse
    form_data = await request.form()
    # Check query string first, then request body, fallback to caller phone
    # Make sure to handle potential spaces if '+' was unencoded in query param
    raw_phone = request.query_params.get("phone")
    if raw_phone and raw_phone.startswith(" "):
        raw_phone = "+" + raw_phone[1:]
    
    caller_phone = raw_phone or form_data.get("From", "+919876543210")
    lang = user_language_pref.get(caller_phone, "en")

    session = session_service.get_or_create_session(caller_phone)
    response = VoiceResponse()

    if session.last_answer_text == "PENDING_PROCESSING":
        # Still generating — play holding status and loop back to fetch_answer
        if lang == "hi":
            response.say("Kanooni jankari taiyar ho rahi hai. Kripya thoda intazaar karein...", voice="Polly.Aditi", language="hi-IN")
        else:
            response.say("Still preparing your answer. Please hold...", voice="Polly.Aditi", language="en-IN")
        response.pause(length=3)
        encoded_phone = urllib.parse.quote_plus(caller_phone)
        response.redirect(url=f"/api/v1/twilio/fetch_answer?phone={encoded_phone}", method="POST")
        return Response(content=str(response), media_type="application/xml")

    # Clean and deliver completed answer
    answer_text = session.last_answer_text or "Your question has been processed."
    clean_text = answer_text.replace("*", "").replace("#", "").replace("_", "").replace("&", "and")

    gather = Gather(num_digits=1, action="/api/v1/twilio/voice", method="POST", timeout=10)
    gather.say(clean_text, voice="Polly.Aditi", language="hi-IN" if lang == "hi" else "en-IN")
    response.append(gather)
    return Response(content=str(response), media_type="application/xml")

