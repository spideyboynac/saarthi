from fastapi import APIRouter, Request, Response
try:
    from twilio.twiml.voice_response import VoiceResponse, Gather, Record
    HAS_TWILIO = True
except ImportError:
    HAS_TWILIO = False

from app.services.action_handler import action_handler_engine
from app.services.session_service import session_service

router = APIRouter(prefix="/twilio", tags=["Twilio IVR"])

@router.post("/voice")
async def twilio_voice_webhook(request: Request):
    """
    Twilio Voice Webhook handling the 7-Action IVR Map via phone keypad (digits 0-6).
    Enforces nested <Gather> for mid-playback barge-in and first-time caller disclaimer.
    """
    form_data = await request.form()
    digits = form_data.get("Digits")
    caller_phone = form_data.get("From", "+919876543210")

    profile = session_service.get_or_create_profile(caller_phone)

    if HAS_TWILIO:
        response = VoiceResponse()

        # Step 2: First-time caller onboarding disclaimer plays once
        if profile.first_time_caller:
            response.say("Welcome to Nyaya Dhwani Legal Literacy Service. Disclaimer: I am an AI legal assistant, not a lawyer. I can explain laws but cannot provide legal representation.")
            session_service.mark_onboarding_completed(caller_phone)

        if not digits:
            # Nested Gather for barge-in
            gather = Gather(num_digits=1, action="/api/v1/twilio/voice", method="POST", timeout=5)
            gather.say("Main menu: Press 1 to ask a question. Press 2 when done speaking. Press 3 to repeat. Press 4 to simplify. Press 5 for follow-ups. Press 6 to stop. Press 0 for legal aid handoff.")
            response.append(gather)
            return Response(content=str(response), media_type="application/xml")

        action_code = int(digits)

        if action_code == 0:
            # Key 0: Human handoff with structured summary
            summary = session_service.get_or_create_session(caller_phone).last_answer_text or "No query recorded."
            handoff_text = f"Connecting you to the District Legal Services Authority (DLSA). Session Summary: {summary[:100]}"
            response.say(handoff_text)
            response.hangup()
            return Response(content=str(response), media_type="application/xml")

        if action_code == 1:
            # Key 1: Ask new question -> start recording
            response.say("Please speak your legal question after the tone. Press 2 when done.")
            response.record(action="/api/v1/twilio/voice?finish=1", finish_on_key="2", max_length=30)
            return Response(content=str(response), media_type="application/xml")

        if action_code == 6:
            response.say("Playback stopped immediately.")
            response.hangup()
            return Response(content=str(response), media_type="application/xml")

        # Process actions 2, 3, 4, 5
        action_res = action_handler_engine.process_action(
            phone_identifier=caller_phone,
            action_code=action_code,
            payload="Consumer court product complaint" if action_code in (1, 2) else None
        )

        # BARGE-IN FIX: Nest <Say> INSIDE <Gather> so keypress interrupts playback immediately
        gather = Gather(num_digits=1, action="/api/v1/twilio/voice", method="POST", timeout=5)
        gather.say(action_res.answer_text)
        response.append(gather)

        return Response(content=str(response), media_type="application/xml")
    else:
        # Fallback TwiML XML generator
        disclaimer_xml = ""
        if profile.first_time_caller:
            disclaimer_xml = "<Say>Welcome to Nyaya Dhwani. Disclaimer: I am an AI legal assistant, not a lawyer.</Say>"
            session_service.mark_onboarding_completed(caller_phone)

        if not digits:
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    {disclaimer_xml}
    <Gather numDigits="1" action="/api/v1/twilio/voice" method="POST" timeout="5">
        <Say>Nyaya Dhwani Menu: Press 1 to ask a question, 2 when done speaking, 3 to repeat, 4 to simplify, 5 for follow-ups, 6 to stop, 0 for legal aid handoff.</Say>
    </Gather>
</Response>"""
        else:
            action_code = int(digits)
            if action_code == 0:
                xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Connecting to District Legal Services Authority DLSA legal aid helpline...</Say>
    <Hangup/>
</Response>"""
            elif action_code == 6:
                xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Playback stopped.</Say>
    <Hangup/>
</Response>"""
            else:
                action_res = action_handler_engine.process_action(
                    phone_identifier=caller_phone,
                    action_code=action_code,
                    payload="Unpaid wage complaint" if action_code in (1, 2) else None
                )
                xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="1" action="/api/v1/twilio/voice" method="POST" timeout="5">
        <Say>{action_res.answer_text}</Say>
    </Gather>
</Response>"""
        return Response(content=xml_content, media_type="application/xml")

