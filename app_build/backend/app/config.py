import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Nyaya-Dhwani Legal Literacy Agent"
    VERSION: str = "2.0.0"
    API_PREFIX: str = "/api/v1"
    
    # Hybrid Routing Config
    CLAUDE_API_URL: str = os.getenv("CLAUDE_API_URL", "https://api.anthropic.com/v1/messages")
    CLAUDE_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    
    # Force Offline Mode flag (for testing offline fallback)
    FORCE_OFFLINE: bool = os.getenv("FORCE_OFFLINE", "false").lower() == "true"
    
    # Session TTL in seconds (Default: 15 minutes)
    SESSION_TTL_SECONDS: int = 900

settings = Settings()
