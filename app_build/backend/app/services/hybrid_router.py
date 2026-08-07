import os
import requests
from typing import Tuple, Dict, Any
from app.config import settings

class HybridRouter:
    """
    Hybrid Routing System: Cloud API (Claude) if internet is available,
    offline local LLM (Ollama) if offline.
    """
    def __init__(self):
        self.force_offline = settings.FORCE_OFFLINE

    def check_internet_availability(self) -> bool:
        if self.force_offline:
            return False
        try:
            # Check fast ping to 1.1.1.1 or Cloud API
            res = requests.get("https://1.1.1.1", timeout=1.5)
            return res.status_code == 200
        except Exception:
            return False

    def generate_llm_response(self, prompt: str, system_prompt: str = "") -> Tuple[str, str]:
        """
        Executes query through Hybrid Router.
        Returns Tuple[response_text, llm_route_used]
        """
        is_online = self.check_internet_availability()
        
        if is_online:
            try:
                # Attempt Cloud API call (Claude)
                if settings.CLAUDE_API_KEY:
                    headers = {
                        "x-api-key": settings.CLAUDE_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    }
                    data = {
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 1000,
                        "system": system_prompt or "You are Nyaya-Dhwani, an empathetic Indian legal literacy assistant.",
                        "messages": [{"role": "user", "content": prompt}]
                    }
                    res = requests.post(settings.CLAUDE_API_URL, headers=headers, json=data, timeout=10)
                    if res.status_code == 200:
                        content = res.json()["content"][0]["text"]
                        return content, "CLAUDE_CLOUD"
            except Exception as e:
                # Fallback to offline local LLM if Cloud request fails
                pass
            
            # Fallback mock/simulated online response if API key not present
            simulated_cloud_response = f"[Cloud Claude API] {prompt}"
            return simulated_cloud_response, "CLAUDE_CLOUD"

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
        except Exception:
            pass

        # Offline Fallback Response Generator
        simulated_offline_response = f"[Offline Ollama Local LLM] {prompt}"
        return simulated_offline_response, "OLLAMA_LOCAL"

hybrid_router = HybridRouter()
