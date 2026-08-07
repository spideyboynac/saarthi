"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.sessionManager = void 0;
class SessionManager {
    sessions = new Map();
    /**
     * Retrieves or initializes a session for a given ID.
     */
    getOrCreate(sessionId) {
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
    update(sessionId, updates) {
        const session = this.getOrCreate(sessionId);
        const updatedSession = { ...session, ...updates };
        this.sessions.set(sessionId, updatedSession);
        return updatedSession;
    }
    /**
     * Adds an entry to the call history log.
     */
    logAction(sessionId, action) {
        const session = this.getOrCreate(sessionId);
        session.callHistory.push(`${new Date().toISOString()}: ${action}`);
    }
    /**
     * Cleans up the session when a call terminates.
     */
    remove(sessionId) {
        this.sessions.delete(sessionId);
    }
}
exports.sessionManager = new SessionManager();
