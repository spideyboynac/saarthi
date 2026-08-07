"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const register_1 = require("./register");
const backendService_1 = require("../backendService");
const sessionManager_1 = require("../sessionManager");
const langResources_1 = require("../../utils/langResources");
(0, register_1.registerHandler)('5', async (context) => {
    const { twiml, session, sessionId, publicUrl } = context;
    const lang = langResources_1.resources[session.language];
    try {
        const result = await backendService_1.BackendService.getFollowups(sessionId);
        if (result.questions && result.questions.length > 0) {
            twiml.say({ voice: lang.voice, language: lang.langCode }, lang.followupPrompt);
            result.questions.forEach((q, index) => {
                twiml.say({ voice: lang.voice, language: lang.langCode }, `Option ${index + 1}: ${q}`);
            });
            sessionManager_1.sessionManager.logAction(sessionId, `Read followups: ${JSON.stringify(result.questions)}`);
        }
        else {
            twiml.say({ voice: lang.voice, language: lang.langCode }, lang.noFollowups);
        }
    }
    catch (error) {
        console.error('Error fetching followups:', error);
        twiml.say({ voice: lang.voice, language: lang.langCode }, lang.followupError);
    }
    // Redirect back to main menu
    twiml.redirect(`${publicUrl}/twilio/menu`);
});
