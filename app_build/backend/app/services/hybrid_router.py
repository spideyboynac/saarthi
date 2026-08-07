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
        Executes query through Hybrid Router.
        Returns Tuple[response_text, llm_route_used]
        """
        is_online = self.check_internet_availability()
        
        if is_online:
            # Check Anthropic Key (user provided ANTHROPIC_API_KEY)
            api_key = settings.CLAUDE_API_KEY or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY is not set. Cannot execute real LLM call.")
                
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            data = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1000,
                "system": system_prompt or "You are Nyaya-Dhwani, an empathetic Indian legal literacy assistant.",
                "messages": [{"role": "user", "content": prompt}]
            }
            try:
                res = requests.post(settings.CLAUDE_API_URL, headers=headers, json=data, timeout=10)
                if res.status_code == 200:
                    content = res.json()["content"][0]["text"]
                    return content, "CLAUDE_CLOUD"
                else:
                    raise RuntimeError(f"Claude API failed with status {res.status_code}: {res.text}")
            except Exception as e:
                raise RuntimeError(f"Cloud LLM request failed: {e}")

        # Offline Local LLM (Ollama) Route
        try:
            ollama_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": f"{system_prompt}\n\n{prompt}",
                "stream": False
            }
            res = requests.post(ollama_url, json=payload, timeout=8)
            if res.status_code == 200:
                text = res.json().get("response", "")
                return text, "OLLAMA_LOCAL"
            else:
                raise RuntimeError(f"Ollama failed with status {res.status_code}: {res.text}")
        except Exception as e:
            raise RuntimeError(f"Offline LLM request failed: {e}")

hybrid_router = HybridRouter()
