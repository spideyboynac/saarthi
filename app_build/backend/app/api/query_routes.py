from fastapi import APIRouter, HTTPException
from app.models.schemas import ActionRequest, ActionResponse, QueryRequest
from app.services.action_handler import action_handler_engine
from app.services.session_service import session_service
from app.services.hybrid_router import hybrid_router

router = APIRouter(prefix="/query", tags=["Query & 6-Action API"])

@router.post("/action", response_model=ActionResponse)
def execute_action(req: ActionRequest):
    """
    Executes any of the 6 actions from the SPA Frontend or API client.
    """
    if req.action_code not in range(1, 7):
        raise HTTPException(status_code=400, detail="Action code must be between 1 and 6.")
    
    return action_handler_engine.process_action(
        phone_identifier=req.phone_hash,
        action_code=req.action_code,
        payload=req.payload
    )

@router.get("/session/{phone_identifier}")
def get_session_info(phone_identifier: str):
    """
    Retrieves short-TTL call_session state object.
    """
    session = session_service.get_or_create_session(phone_identifier)
    return {
        "call_session": {
            "phone_hash": session.phone_hash,
            "last_answer_text": session.last_answer_text,
            "last_answer_tier": session.last_answer_tier,
            "call_active": session.call_active
        },
        "llm_route": "CLAUDE_CLOUD" if hybrid_router.check_internet_availability() else "OLLAMA_LOCAL"
    }
