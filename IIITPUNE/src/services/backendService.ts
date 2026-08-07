import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

/**
 * FastAPI backend base URL.
 * Override via FASTAPI_URL env var (e.g. in production/ngrok).
 */
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';
const ACTION_ENDPOINT = `${FASTAPI_URL}/api/v1/query/action`;

// ─── Action codes (mirror of app_build/backend action_handler.py) ─────────────
// 1/2 = New Question (RAG), 3 = Repeat, 4 = Simplify, 5 = Follow-ups, 6 = Stop
const ACTION_QUERY    = 2;
const ACTION_SIMPLIFY = 4;
const ACTION_FOLLOWUP = 5;

// ─── FastAPI ActionResponse schema ────────────────────────────────────────────
interface FastAPIActionResponse {
  action_code: number;
  action_name: string;
  answer_text: string;           // primary answer field in ActionResponse
  literacy_tier: string;
  rag_executed: boolean;
  llm_route: string;
  call_active: boolean;
  socratic_followups?: string[]; // populated for action 5
  confidence_score?: string;
}

// ─── Public interface types (used by twilioController) ───────────────────────
export interface QueryResponse {
  answer: string;
}

export interface SimplifyResponse {
  answer: string;
}

export interface FollowupsResponse {
  questions: string[];
}

// ─── Helper ──────────────────────────────────────────────────────────────────
async function callAction(
  phone_hash: string,
  action_code: number,
  payload: string | null
): Promise<FastAPIActionResponse> {
  const requestBody = { phone_hash, action_code, payload };
  console.log(`[BackendService] POST ${ACTION_ENDPOINT}`, JSON.stringify(requestBody));

  const response = await axios.post<FastAPIActionResponse>(ACTION_ENDPOINT, requestBody, {
    timeout: 30_000,
    headers: { 'Content-Type': 'application/json' },
  });

  console.log(`[BackendService] Response (${response.status}):`, JSON.stringify(response.data).slice(0, 300));
  return response.data;
}

// ─── Public service methods ───────────────────────────────────────────────────
export class BackendService {
  /**
   * Action 2 — Send the user's voice transcript to the RAG engine.
   * payload = the raw transcript string (matches ActionRequest.payload: Optional[str])
   */
  public static async query(transcript: string, sessionId: string): Promise<QueryResponse> {
    try {
      const data = await callAction(sessionId, ACTION_QUERY, transcript);
      return { answer: data.answer_text || 'Sorry, I could not find an answer to your question.' };
    } catch (error) {
      console.error('[BackendService] query() failed:', error);
      return { answer: 'The legal assistant is temporarily unavailable. Please try again shortly.' };
    }
  }

  /**
   * Action 4 — Simplify the previous answer into plain language.
   * The payload is ignored by the backend (it uses session state), so we pass null.
   */
  public static async simplify(previousAnswer: string, sessionId: string): Promise<SimplifyResponse> {
    try {
      const data = await callAction(sessionId, ACTION_SIMPLIFY, null);
      return { answer: data.answer_text || previousAnswer };
    } catch (error) {
      console.error('[BackendService] simplify() failed:', error);
      return { answer: previousAnswer }; // fallback: replay original
    }
  }

  /**
   * Action 5 — Get Socratic follow-up questions.
   * The payload is ignored by the backend (it uses session state), so we pass null.
   */
  public static async getFollowups(sessionId: string): Promise<FollowupsResponse> {
    try {
      const data = await callAction(sessionId, ACTION_FOLLOWUP, null);
      const questions = data.socratic_followups ?? [];
      return { questions };
    } catch (error) {
      console.error('[BackendService] getFollowups() failed:', error);
      return { questions: [] };
    }
  }
}
