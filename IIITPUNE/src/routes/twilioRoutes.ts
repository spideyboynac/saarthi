import { Router } from 'express';
import { TwilioController } from '../controllers/twilioController';

const router = Router();

// Handle incoming phone call (Language Selection Menu)
router.post('/incoming', TwilioController.incomingCall);
router.get('/incoming', TwilioController.incomingCall);

// Handle language choice selection
router.post('/language-select', TwilioController.languageSelect);
router.get('/language-select', TwilioController.languageSelect);

// Handle main welcome/keypad menu playout
router.post('/menu', TwilioController.menu);
router.get('/menu', TwilioController.menu);

// Handle menu digit key selection
router.post('/menu-select', TwilioController.menuSelect);
router.get('/menu-select', TwilioController.menuSelect);

// Handle speech input transcript processing
router.post('/record-speech', TwilioController.recordSpeech);
router.get('/record-speech', TwilioController.recordSpeech);

export default router;
