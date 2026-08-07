"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.TwilioController = void 0;
const twilio_1 = __importDefault(require("twilio"));
const sessionManager_1 = require("../services/sessionManager");
const keypad_1 = require("../services/keypad");
const backendService_1 = require("../services/backendService");
const langResources_1 = require("../utils/langResources");
const getPublicUrl = () => process.env.PUBLIC_URL || 'http://localhost:3000';
class TwilioController {
    /**
     * Endpoint /twilio/incoming
     * Language Selection Menu (the very first step of the call)
     */
    static async incomingCall(req, res) {
        const twiml = new twilio_1.default.twiml.VoiceResponse();
        const sessionId = (req.body.CallSid || req.query.CallSid || 'test-session');
        // Reset or initialize session state
        sessionManager_1.sessionManager.remove(sessionId);
        const session = sessionManager_1.sessionManager.getOrCreate(sessionId);
        sessionManager_1.sessionManager.logAction(sessionId, 'Call started. Prompting for language choice.');
        // Gather 1 digit for language selection
        const gather = twiml.gather({
            numDigits: 1,
            action: `${getPublicUrl()}/twilio/language-select`,
            method: 'POST',
            timeout: 6,
        });
        // Prompt in both English and Hindi
        gather.say({ voice: 'Polly.Aditi', language: 'en-IN' }, 'For English, press 1.');
        gather.say({ voice: 'Polly.Madhur', language: 'hi-IN' }, 'हिंदी के लिए, दो दबाएं।');
        // If they don't press anything
        twiml.say({ voice: 'Polly.Aditi', language: 'en-IN' }, 'No input detected. Goodbye.');
        twiml.hangup();
        res.type('text/xml');
        res.send(twiml.toString());
    }
    /**
     * Endpoint /twilio/language-select
     * Saves chosen language to session and forwards to menu.
     */
    static async languageSelect(req, res) {
        const twiml = new twilio_1.default.twiml.VoiceResponse();
        const sessionId = (req.body.CallSid || req.query.CallSid || 'test-session');
        const digit = (req.body.Digits || req.query.Digits);
        sessionManager_1.sessionManager.logAction(sessionId, `Selected language digit: ${digit}`);
        let selectedLang = 'en'; // default
        if (digit === '2') {
            selectedLang = 'hi';
        }
        // Save language to session
        sessionManager_1.sessionManager.update(sessionId, { language: selectedLang });
        sessionManager_1.sessionManager.logAction(sessionId, `Language set to: ${selectedLang}`);
        // Redirect to main menu
        twiml.redirect(`${getPublicUrl()}/twilio/menu`);
        res.type('text/xml');
        res.send(twiml.toString());
    }
    /**
     * Endpoint /twilio/menu
     * Welcomes user and plays options in their selected language.
     */
    static async menu(req, res) {
        const twiml = new twilio_1.default.twiml.VoiceResponse();
        const sessionId = (req.body.CallSid || req.query.CallSid || 'test-session');
        const session = sessionManager_1.sessionManager.getOrCreate(sessionId);
        const lang = langResources_1.resources[session.language];
        sessionManager_1.sessionManager.update(sessionId, { conversationState: 'menu' });
        sessionManager_1.sessionManager.logAction(sessionId, `Loaded main menu in language: ${session.language}`);
        // Gather keypad selection
        const gather = twiml.gather({
            numDigits: 1,
            action: `${getPublicUrl()}/twilio/menu-select`,
            method: 'POST',
            timeout: 8,
        });
        gather.say({ voice: lang.voice, language: lang.langCode }, lang.welcome);
        gather.say({ voice: lang.voice, language: lang.langCode }, lang.menuOptions);
        // If they don't press anything
        twiml.say({ voice: lang.voice, language: lang.langCode }, lang.noInput);
        twiml.hangup();
        res.type('text/xml');
        res.send(twiml.toString());
    }
    /**
     * Endpoint /twilio/menu-select
     * Handles user's keypad entry.
     */
    static async menuSelect(req, res) {
        const twiml = new twilio_1.default.twiml.VoiceResponse();
        const sessionId = (req.body.CallSid || req.query.CallSid || 'test-session');
        const digit = (req.body.Digits || req.query.Digits);
        const session = sessionManager_1.sessionManager.getOrCreate(sessionId);
        const lang = langResources_1.resources[session.language];
        sessionManager_1.sessionManager.logAction(sessionId, `Pressed key: ${digit}`);
        if (!digit) {
            twiml.say({ voice: lang.voice, language: lang.langCode }, lang.noInput);
            twiml.redirect(`${getPublicUrl()}/twilio/menu`);
            res.type('text/xml');
            return res.send(twiml.toString());
        }
        const handler = (0, keypad_1.getHandler)(digit);
        if (handler) {
            try {
                await handler({
                    sessionId,
                    session,
                    twiml,
                    publicUrl: getPublicUrl(),
                });
            }
            catch (error) {
                console.error(`Error executing handler for key ${digit}:`, error);
                twiml.say({ voice: lang.voice, language: lang.langCode }, lang.error);
                twiml.redirect(`${getPublicUrl()}/twilio/menu`);
            }
        }
        else {
            twiml.say({ voice: lang.voice, language: lang.langCode }, lang.invalidOption);
            twiml.redirect(`${getPublicUrl()}/twilio/menu`);
        }
        res.type('text/xml');
        res.send(twiml.toString());
    }
    /**
     * Endpoint /twilio/record-speech
     * Receives speech recognition transcript, updates session, queries LLM backend,
     * and plays the resulting response.
     */
    static async recordSpeech(req, res) {
        const twiml = new twilio_1.default.twiml.VoiceResponse();
        const sessionId = (req.body.CallSid || req.query.CallSid || 'test-session');
        const transcript = (req.body.SpeechResult || req.query.SpeechResult);
        const session = sessionManager_1.sessionManager.getOrCreate(sessionId);
        const lang = langResources_1.resources[session.language];
        sessionManager_1.sessionManager.logAction(sessionId, `Speech recognized: "${transcript}"`);
        if (!transcript) {
            twiml.say({ voice: lang.voice, language: lang.langCode }, lang.noInput);
            twiml.redirect(`${getPublicUrl()}/twilio/menu`);
            res.type('text/xml');
            return res.send(twiml.toString());
        }
        // Update session state with the transcript
        sessionManager_1.sessionManager.update(sessionId, {
            previousTranscript: transcript,
        });
        try {
            twiml.say({ voice: lang.voice, language: lang.langCode }, lang.processing);
            // Call downstream AI API
            const result = await backendService_1.BackendService.query(transcript, sessionId);
            // Cache the answer
            sessionManager_1.sessionManager.update(sessionId, {
                previousAnswer: result.answer,
            });
            // Play the answer wrapped in a Gather, so they can interrupt by pressing 6 (or any key)
            const playGather = twiml.gather({
                numDigits: 1,
                action: `${getPublicUrl()}/twilio/menu-select`,
                method: 'POST',
                timeout: 4,
            });
            playGather.say({ voice: lang.voice, language: lang.langCode }, `${result.answer}.`);
            // If they listen to the whole answer without pressing a key
            twiml.redirect(`${getPublicUrl()}/twilio/menu`);
        }
        catch (error) {
            console.error('Error fetching AI answer:', error);
            twiml.say({ voice: lang.voice, language: lang.langCode }, lang.error);
            twiml.redirect(`${getPublicUrl()}/twilio/menu`);
        }
        res.type('text/xml');
        res.send(twiml.toString());
    }
}
exports.TwilioController = TwilioController;
