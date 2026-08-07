"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const register_1 = require("./register");
const langResources_1 = require("../../utils/langResources");
(0, register_1.registerHandler)('3', (context) => {
    const { twiml, session, publicUrl } = context;
    const lang = langResources_1.resources[session.language];
    if (session.previousAnswer) {
        twiml.say({ voice: lang.voice, language: lang.langCode }, `${lang.repeating}${session.previousAnswer}`);
    }
    else {
        twiml.say({ voice: lang.voice, language: lang.langCode }, lang.noPreviousAnswer);
    }
    // Redirect back to main menu
    twiml.redirect(`${publicUrl}/twilio/menu`);
});
