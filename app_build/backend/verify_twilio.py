"""
verify_twilio.py — Simulates Twilio webhook calls to localhost:8000.

Usage:
    python verify_twilio.py

Prerequisites:
    - Backend must be running: uvicorn app.main:app --reload
    - Python requests library: pip install requests

This script fires real HTTP POST requests that mimic exactly what Twilio
sends when a caller presses a key or sends an SMS. No real phone needed.
"""

import sys
import requests

BASE = "http://localhost:8000/api/v1"
VOICE_URL = f"{BASE}/twilio/voice"
SMS_URL   = f"{BASE}/twilio/sms"

TEST_PHONE = "+919876543210"

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"

def post_voice(digits=None, finish=False, label=""):
    """POST to /api/v1/twilio/voice, mimicking Twilio's form payload."""
    data = {"From": TEST_PHONE, "CallSid": "CATEST000001"}
    if digits is not None:
        data["Digits"] = str(digits)
    if finish:
        data["RecordingUrl"] = "https://api.twilio.com/fake-recording.wav"
    resp = requests.post(VOICE_URL, data=data, timeout=180)
    return resp


def post_sms(body, label=""):
    """POST to /api/v1/twilio/sms, mimicking Twilio's form payload."""
    data = {"From": TEST_PHONE, "To": "+911234567890", "Body": body}
    resp = requests.post(SMS_URL, data=data, timeout=180)
    return resp


def check(resp, label, must_contain=None, status=200):
    ok = resp.status_code == status
    if must_contain:
        ok = ok and must_contain.lower() in resp.text.lower()
    tag = PASS if ok else FAIL
    print(f"  [{tag}] {label}")
    if not ok:
        print(f"         HTTP {resp.status_code} | body snippet: {resp.text[:200]}")
    return ok


def banner(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def main():
    print("\nNyaya Dhwani — Twilio Webhook Verification")
    print(f"Backend: {BASE}\n")

    try:
        requests.get("http://localhost:8000/docs", timeout=3)
    except Exception:
        print(f"[{FAIL}] Backend is not reachable at localhost:8000. Start uvicorn first.")
        sys.exit(1)

    results = []

    # ─────────────────────────────────────────────────────
    # VOICE WEBHOOK TESTS
    # ─────────────────────────────────────────────────────
    banner("VOICE: Initial menu (no digits)")
    r = post_voice(label="Initial menu")
    results.append(check(r, "Returns 200 + menu XML", must_contain="<Gather"))

    banner("VOICE: Digit 1 — Ask new question (start record)")
    r = post_voice(digits=1, label="Key 1")
    results.append(check(r, "Returns 200 + <Record>", must_contain="<Record"))

    banner("VOICE: Digit 0 — DLSA handoff")
    r = post_voice(digits=0, label="Key 0")
    results.append(check(r, "Returns 200 + DLSA mention", must_contain="Legal Services"))

    banner("VOICE: Digit 3 — Repeat (RAG Bypass, session may be empty)")
    r = post_voice(digits=3, label="Key 3 Repeat")
    results.append(check(r, "Returns 200 + <Say>", must_contain="<Say>"))

    banner("VOICE: Digit 4 — Simplify (RAG Bypass)")
    r = post_voice(digits=4, label="Key 4 Simplify")
    results.append(check(r, "Returns 200 + <Say>", must_contain="<Say>"))

    banner("VOICE: Digit 5 — Follow-ups (RAG Bypass)")
    r = post_voice(digits=5, label="Key 5 Follow-ups")
    results.append(check(r, "Returns 200 + <Say>", must_contain="<Say>"))

    banner("VOICE: Digit 6 — Stop playback / barge-in")
    r = post_voice(digits=6, label="Key 6 Stop")
    results.append(check(r, "Returns 200 + <Hangup>", must_contain="Hangup"))

    # ─────────────────────────────────────────────────────
    # SMS WEBHOOK TESTS
    # ─────────────────────────────────────────────────────
    banner("SMS: HELP command")
    r = post_sms("HELP", label="HELP")
    results.append(check(r, "Returns 200 + menu text", must_contain="ASK"))

    banner("SMS: ASK <legal question>")
    r = post_sms("ASK What is the punishment for theft under BNS?", label="ASK theft")
    # This invokes full Ollama LLM pipeline — may take up to 2 minutes
    print("  [INFO] Invoking full RAG+LLM pipeline — may take 60-120s on CPU...")
    results.append(check(r, "Returns 200 + legal answer", must_contain="<Message>"))

    banner("SMS: REPEAT")
    r = post_sms("REPEAT", label="REPEAT")
    results.append(check(r, "Returns 200 + <Message>", must_contain="<Message>"))

    banner("SMS: SIMPLIFY")
    r = post_sms("SIMPLIFY", label="SIMPLIFY")
    print("  [INFO] Invoking Ollama LLM for simplification — may take 30-60s...")
    results.append(check(r, "Returns 200 + <Message>", must_contain="<Message>"))

    banner("SMS: FOLLOWUP")
    r = post_sms("FOLLOWUP", label="FOLLOWUP")
    print("  [INFO] Invoking Ollama LLM for follow-up questions — may take 30-60s...")
    results.append(check(r, "Returns 200 + follow-up questions", must_contain="<Message>"))

    banner("SMS: DLSA")
    r = post_sms("DLSA", label="DLSA")
    results.append(check(r, "Returns 200 + DLSA mention", must_contain="DLSA"))

    banner("SMS: FULL (complete last answer)")
    r = post_sms("FULL", label="FULL")
    results.append(check(r, "Returns 200 + <Message>", must_contain="<Message>"))

    banner("SMS: STOP")
    r = post_sms("STOP", label="STOP")
    results.append(check(r, "Returns 200 + session ended", must_contain="ended"))

    banner("SMS: Unknown command")
    r = post_sms("DANCE", label="Unknown DANCE")
    results.append(check(r, "Returns 200 + help menu fallback", must_contain="ASK"))

    # ─────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────
    passed = sum(results)
    total  = len(results)
    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed}/{total} passed")
    print('='*60)
    if passed < total:
        print(f"\n  {FAIL} {total - passed} test(s) failed. Check backend logs for details.")
        sys.exit(1)
    else:
        print(f"\n  {PASS} All webhook routes verified successfully.")


if __name__ == "__main__":
    main()
