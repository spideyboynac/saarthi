"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const twilioController_1 = require("../controllers/twilioController");
const router = (0, express_1.Router)();
// Handle incoming phone call (Language Selection Menu)
router.post('/incoming', twilioController_1.TwilioController.incomingCall);
router.get('/incoming', twilioController_1.TwilioController.incomingCall);
// Handle language choice selection
router.post('/language-select', twilioController_1.TwilioController.languageSelect);
router.get('/language-select', twilioController_1.TwilioController.languageSelect);
// Handle main welcome/keypad menu playout
router.post('/menu', twilioController_1.TwilioController.menu);
router.get('/menu', twilioController_1.TwilioController.menu);
// Handle menu digit key selection
router.post('/menu-select', twilioController_1.TwilioController.menuSelect);
router.get('/menu-select', twilioController_1.TwilioController.menuSelect);
// Handle speech input transcript processing
router.post('/record-speech', twilioController_1.TwilioController.recordSpeech);
router.get('/record-speech', twilioController_1.TwilioController.recordSpeech);
exports.default = router;
