from fastapi import APIRouter, Request, Response
try:
    from twilio.twiml.voice_response import VoiceResponse, Gather
    HAS_TWILIO = True
except ImportError:
    HAS_TWILIO = False

from app.services.action_handler import action_handler_engine

router = APIRouter(prefix="/twilio", tags=["Twilio IVR"])

@router.post("/voice")
async def twilio_voice_webhook(request: Request):
    """
    Twilio Voice Webhook handling the 6-Action IVR Map via phone keypad (digits 1-6).
    """
    form_data = await request.form()
    digits = form_data.get("Digits")
    caller_phone = form_data.get("From", "+919876543210")

    if HAS_TWILIO:
        response = VoiceResponse()

        if not digits:
            gather = Gather(num_digits=1, action="/api/v1/twilio/voice", method="POST", timeout=5)
            gather.say("Welcome to Nyaya Dhwani Legal Literacy Service.")
            gather.say("Press 1 to ask a legal question.")
            gather.say("Press 2 when done speaking.")
            gather.say("Press 3 to repeat the last answer.")
            gather.say("Press 4 to simplify the explanation.")
            gather.say("Press 5 for recommended follow up questions.")
            gather.say("Press 6 to stop playback.")
            response.append(gather)
            return Response(content=str(response), media_type="application/xml")

        action_code = int(digits)
        action_res = action_handler_engine.process_action(
            phone_identifier=caller_phone,
            action_code=action_code
        )

        if action_code == 6:
            response.say("Playback stopped. Goodbye.")
            response.hangup()
        else:
            response.say(action_res.answer_text)
            gather = Gather(num_digits=1, action="/api/v1/twilio/voice", method="POST", timeout=5)
            response.append(gather)

        return Response(content=str(response), media_type="application/xml")
    else:
        # Fallback TwiML XML string generator without twilio package
        if not digits:
            xml_content = """<?xml stroke="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="1" action="/api/v1/twilio/voice" method="POST" timeout="5">
        <Say>Welcome to Nyaya Dhwani Legal Literacy Service. Press 1 to 6 for action controls.</Say>
    </Gather>
</Response>"""
        else:
            action_code = int(digits)
            action_res = action_handler_engine.process_action(
                phone_identifier=caller_phone,
                action_code=action_code
            )
            xml_content = f"""<?xml stroke="1.0" encoding="UTF-8"?>
<Response>
    <Say>{action_res.answer_text}</Say>
</Response>"""
        return Response(content=xml_content, media_type="application/xml")

