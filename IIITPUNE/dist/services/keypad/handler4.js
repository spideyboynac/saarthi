"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const register_1 = require("./register");
const backendService_1 = require("../backendService");
const sessionManager_1 = require("../sessionManager");
const langResources_1 = require("../../utils/langResources");
(0, register_1.registerHandler)('4', async (context) => {
    const { twiml, session, sessionId, publicUrl } = context;
    const lang = langResources_1.resources[session.language];
    if (!session.previousAnswer) {
        twiml.say({ voice: lang.voice, language: lang.langCode }, lang.noPreviousAnswer);
        twiml.redirect(`${publicUrl}/twilio/menu`);
        return;
    }
    try {
        twiml.say({ voice: lang.voice, language: lang.langCode }, lang.simplifying);
        const result = await backendService_1.BackendService.simplify(session.previousAnswer, sessionId);
        // Play simplified answer
        twiml.say({ voice: lang.voice, language: lang.langCode }, result.answer);
        // Update session state
        sessionManager_1.sessionManager.update(sessionId, {
            previousAnswer: result.answer,
        });
        sessionManager_1.sessionManager.logAction(sessionId, `Simplified previous response to: "${result.answer}"`);
    }
    catch (error) {
        console.error('Error during simplify:', error);
        twiml.say({ voice: lang.voice, language: lang.langCode }, lang.simplifyError);
    }
    // Redirect back to main menu
    twiml.redirect(`${publicUrl}/twilio/menu`);
});
