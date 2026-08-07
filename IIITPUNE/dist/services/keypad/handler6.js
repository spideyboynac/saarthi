"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const register_1 = require("./register");
const sessionManager_1 = require("../sessionManager");
const langResources_1 = require("../../utils/langResources");
(0, register_1.registerHandler)('6', (context) => {
    const { twiml, session, sessionId, publicUrl } = context;
    const lang = langResources_1.resources[session.language];
    sessionManager_1.sessionManager.logAction(sessionId, 'Interrupted and stopped playback.');
    twiml.say({ voice: lang.voice, language: lang.langCode }, lang.stopped);
    twiml.redirect(`${publicUrl}/twilio/menu`);
});
