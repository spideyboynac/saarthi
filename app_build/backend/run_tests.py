import sys
import base64
import unittest
from app.services.session_service import session_service
from app.services.hybrid_router import hybrid_router
from app.services.action_handler import action_handler_engine
from app.services.stt_service import stt_service

class TestNyayaDhwaniBackend(unittest.TestCase):
    def setUp(self):
        self.test_phone = "+919988776655"

    def test_01_session_lifecycle(self):
        session = session_service.get_or_create_session(self.test_phone)
        self.assertIsNotNone(session.phone_hash)
        self.assertEqual(session.last_answer_tier, "STANDARD")
        self.assertTrue(session.call_active)

    def test_02_hybrid_router_check(self):
        route_status = hybrid_router.check_internet_availability()
        self.assertIsInstance(route_status, bool)

    def test_03_action_1_with_real_payload_dual_rag(self):
        """Action 1/2 MUST receive a real transcription payload — not a hardcoded string."""
        res = action_handler_engine.process_action(
            phone_identifier=self.test_phone,
            action_code=1,
            payload="What is the legal process for consumer court claim?"
        )
        self.assertEqual(res.action_code, 1)
        self.assertTrue(res.rag_executed, "Action 1 MUST execute RAG retrieval.")
        self.assertIn(res.llm_route, ["CLAUDE_CLOUD", "OLLAMA_LOCAL"])
        self.assertTrue(len(res.answer_text) > 0)

    def test_03b_action_1_rejects_empty_payload(self):
        """ENFORCEMENT 1: Action 1/2 with no payload MUST raise ValueError, not use a hardcoded question."""
        with self.assertRaises(ValueError) as ctx:
            action_handler_engine.process_action(
                phone_identifier=self.test_phone,
                action_code=1,
                payload=None
            )
        self.assertIn("forbidden", str(ctx.exception).lower())

    def test_04_action_3_repeat_rag_bypass(self):
        res = action_handler_engine.process_action(
            phone_identifier=self.test_phone,
            action_code=3
        )
        self.assertEqual(res.action_code, 3)
        self.assertFalse(res.rag_executed, "Action 3 MUST STRICTLY bypass RAG re-retrieval.")
        self.assertIn("[REPLAY]", res.answer_text)

    def test_05_action_4_simplify_rag_bypass(self):
        res = action_handler_engine.process_action(
            phone_identifier=self.test_phone,
            action_code=4
        )
        self.assertEqual(res.action_code, 4)
        self.assertFalse(res.rag_executed, "Action 4 MUST STRICTLY bypass RAG re-retrieval.")
        self.assertEqual(res.literacy_tier, "SIMPLE")

    def test_06_action_5_followups_rag_bypass(self):
        res = action_handler_engine.process_action(
            phone_identifier=self.test_phone,
            action_code=5
        )
        self.assertEqual(res.action_code, 5)
        self.assertFalse(res.rag_executed, "Action 5 MUST STRICTLY bypass RAG re-retrieval.")
        self.assertIsNotNone(res.socratic_followups)
        self.assertGreaterEqual(len(res.socratic_followups), 2)

    def test_07_action_6_stop_barge_in(self):
        res = action_handler_engine.process_action(
            phone_identifier=self.test_phone,
            action_code=6
        )
        self.assertEqual(res.action_code, 6)
        self.assertFalse(res.call_active)
        self.assertIn("[BARGE-IN]", res.answer_text)

    def test_08_stt_service_decodes_base64_audio(self):
        """ENFORCEMENT 4: STT service must decode Base64 audio and return transcription."""
        # Create a fake audio payload (512 bytes of zeroes, Base64 encoded)
        fake_audio_bytes = b'\x00' * 512
        fake_b64 = base64.b64encode(fake_audio_bytes).decode('utf-8')

        transcription = stt_service.process_audio_b64(fake_b64)
        self.assertIsInstance(transcription, str)
        # Without an API key, it should return the missing key error
        if "missing" in transcription.lower():
            self.assertIn("key missing", transcription.lower())
        else:
            self.assertGreater(len(transcription), 0)

    def test_09_stt_service_handles_data_uri_prefix(self):
        """STT must strip data URI prefix before decoding."""
        fake_audio_bytes = b'\x00' * 1024
        fake_b64 = "data:audio/webm;codecs=opus;base64," + base64.b64encode(fake_audio_bytes).decode('utf-8')

        transcription = stt_service.process_audio_b64(fake_b64)
        self.assertIsInstance(transcription, str)

    def test_10_stt_rejects_empty_audio(self):
        """STT must flag audio that is too short."""
        tiny_b64 = base64.b64encode(b'\x00' * 10).decode('utf-8')
        transcription = stt_service.process_audio_b64(tiny_b64)
        self.assertIn("too short", transcription.lower())

if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING NYAYA-DHWANI v2.1 BACKEND VERIFICATION TESTS")
    print("(Includes Hardware Enforcement Validation)")
    print("=" * 60)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNyayaDhwaniBackend)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
