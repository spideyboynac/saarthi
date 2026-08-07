export interface SessionState {
  sessionId: string; // Typically CallSid from Twilio
  language: 'en' | 'hi';
  previousTranscript?: string;
  previousAnswer?: string;
  callHistory: string[];
  conversationState: 'welcome' | 'menu' | 'recording' | 'playing' | 'idle';
}

class SessionManager {
  private sessions: Map<string, SessionState> = new Map();

  /**
   * Retrieves or initializes a session for a given ID.
   */
  public getOrCreate(sessionId: string): SessionState {
    let session = this.sessions.get(sessionId);
    if (!session) {
      session = {
        sessionId,
        language: 'en',
        callHistory: [],
        conversationState: 'welcome',
      };
      this.sessions.set(sessionId, session);
    }
    return session;
  }

  /**
   * Updates an existing session with partial state.
   */
  public update(sessionId: string, updates: Partial<SessionState>): SessionState {
    const session = this.getOrCreate(sessionId);
    const updatedSession = { ...session, ...updates };
    this.sessions.set(sessionId, updatedSession);
    return updatedSession;
  }

  /**
   * Adds an entry to the call history log.
   */
  public logAction(sessionId: string, action: string): void {
    const session = this.getOrCreate(sessionId);
    session.callHistory.push(`${new Date().toISOString()}: ${action}`);
  }

  /**
   * Cleans up the session when a call terminates.
   */
  public remove(sessionId: string): void {
    this.sessions.delete(sessionId);
  }
}

export const sessionManager = new SessionManager();
