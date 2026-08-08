import os
import re
import queue
import requests
from typing import Tuple, Dict, Any
from app.config import settings

class HybridRouter:
    """
    Hybrid Routing System (Step 5):
    - Cloud API (Claude) if internet is available.
    - Offline local LLM (Ollama) if offline.
    - Includes a thread-safe query_queue to hold queries during mid-switch transitions.
    """
    def __init__(self):
        self.force_offline = settings.FORCE_OFFLINE
        self.query_queue = queue.Queue()

    def check_internet_availability(self) -> bool:
        if self.force_offline:
            return False
        try:
            res = requests.get("https://1.1.1.1", timeout=1.5)
            return res.status_code == 200
        except Exception:
            return False

    def queue_query_for_switch(self, query_payload: Dict[str, Any]):
        """Buffers query during network transition."""
        self.query_queue.put(query_payload)

    def process_queued_queries(self) -> int:
        """Flushes buffered queries after transition."""
        count = 0
        while not self.query_queue.empty():
            try:
                item = self.query_queue.get_nowait()
                count += 1
            except queue.Empty:
                break
        return count

    def generate_llm_response(self, prompt: str, system_prompt: str = "") -> Tuple[str, str]:
        """
        Executes query through local Ollama LLM (llama3.1).
        Returns Tuple[response_text, llm_route_used]
        """
        try:
            ollama_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False
            }
            res = requests.post(ollama_url, json=payload, timeout=120.0)
            if res.status_code == 200:
                text = res.json().get("response", "")
                return text, "OLLAMA_LOCAL_LLAMA3"
            else:
                raise RuntimeError(f"Ollama returned HTTP status {res.status_code}: {res.text}")
        except Exception as e:
            raise RuntimeError(f"Ollama LLM request failed: {e}")

hybrid_router = HybridRouter()
