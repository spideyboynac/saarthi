import { Request, Response } from 'express';
import twilio from 'twilio';
import { sessionManager } from '../services/sessionManager';
import { getHandler } from '../services/keypad';
import { BackendService } from '../services/backendService';
import { resources } from '../utils/langResources';

const getPublicUrl = () => process.env.PUBLIC_URL || 'http://localhost:3000';

export class TwilioController {
  /**
   * Endpoint /twilio/incoming
   * Language Selection Menu (the very first step of the call)
   */
  public static async incomingCall(req: Request, res: Response) {
    const twiml = new twilio.twiml.VoiceResponse();
    const sessionId = (req.body.CallSid || req.query.CallSid || 'test-session') as string;

    // Reset or initialize session state
    sessionManager.remove(sessionId);
    const session = sessionManager.getOrCreate(sessionId);
    sessionManager.logAction(sessionId, 'Call started. Prompting for language choice.');

    // Gather 1 digit for language selection
    const gather = twiml.gather({
      numDigits: 1,
      action: `${getPublicUrl()}/twilio/language-select`,
      method: 'POST',
      timeout: 6,
    });

    // Prompt in both English first, then Hindi (using Polly.Aditi which is bilingual)
    gather.say(
      { voice: 'Polly.Aditi' as any, language: 'en-IN' as any },
      'For English, press 1. For Hindi, press 2.'
    );
    gather.say(
      { voice: 'Polly.Aditi' as any, language: 'hi-IN' as any },
      'English ke liye ek dabaye. Hindi ke liye do dabaye.'
    );

    // If they don't press anything
    twiml.say(
      { voice: 'Polly.Aditi', language: 'en-IN' },
      'No input detected. Goodbye.'
    );
    twiml.hangup();

    res.type('text/xml');
    res.send(twiml.toString());
  }

  /**
   * Endpoint /twilio/language-select
   * Saves chosen language to session and forwards to menu.
   */
  public static async languageSelect(req: Request, res: Response) {
    const twiml = new twilio.twiml.VoiceResponse();
    const sessionId = (req.body.CallSid || req.query.CallSid || 'test-session') as string;
    const digit = (req.body.Digits || req.query.Digits) as string;

    sessionManager.logAction(sessionId, `Selected language digit: ${digit}`);

    let selectedLang: 'en' | 'hi' = 'en'; // default
    if (digit === '2') {
      selectedLang = 'hi';
    }

    // Save language to session
    sessionManager.update(sessionId, { language: selectedLang });
    sessionManager.logAction(sessionId, `Language set to: ${selectedLang}`);

    // Redirect to main menu
    twiml.redirect(`${getPublicUrl()}/twilio/menu`);

    res.type('text/xml');
    res.send(twiml.toString());
  }

  /**
   * Endpoint /twilio/menu
   * Welcomes user and plays options in their selected language.
   */
  public static async menu(req: Request, res: Response) {
    const twiml = new twilio.twiml.VoiceResponse();
    const sessionId = (req.body.CallSid || req.query.CallSid || 'test-session') as string;

    const session = sessionManager.getOrCreate(sessionId);
    const lang = resources[session.language];
    
    sessionManager.update(sessionId, { conversationState: 'menu' });
    sessionManager.logAction(sessionId, `Loaded main menu in language: ${session.language}`);

    // Gather keypad selection
    const gather = twiml.gather({
      numDigits: 1,
      action: `${getPublicUrl()}/twilio/menu-select`,
      method: 'POST',
      timeout: 8,
    });

    gather.say(
      { voice: lang.voice, language: lang.langCode },
      lang.welcome
    );

    gather.say(
      { voice: lang.voice, language: lang.langCode },
      lang.menuOptions
    );

    // If they don't press anything
    twiml.say(
      { voice: lang.voice, language: lang.langCode },
      lang.noInput
    );
    twiml.hangup();

    res.type('text/xml');
    res.send(twiml.toString());
  }

  /**
   * Endpoint /twilio/menu-select
   * Handles user's keypad entry.
   */
  public static async menuSelect(req: Request, res: Response) {
    const twiml = new twilio.twiml.VoiceResponse();
    const sessionId = (req.body.CallSid || req.query.CallSid || 'test-session') as string;
    const digit = (req.body.Digits || req.query.Digits) as string;

    const session = sessionManager.getOrCreate(sessionId);
    const lang = resources[session.language];
    sessionManager.logAction(sessionId, `Pressed key: ${digit}`);

    if (!digit) {
      twiml.say(
        { voice: lang.voice, language: lang.langCode },
        lang.noInput
      );
      twiml.redirect(`${getPublicUrl()}/twilio/menu`);
      res.type('text/xml');
      return res.send(twiml.toString());
    }

    const handler = getHandler(digit);
    if (handler) {
      try {
        await handler({
          sessionId,
          session,
          twiml,
          publicUrl: getPublicUrl(),
        });
      } catch (error) {
        console.error(`Error executing handler for key ${digit}:`, error);
        twiml.say(
          { voice: lang.voice, language: lang.langCode },
          lang.error
        );
        twiml.redirect(`${getPublicUrl()}/twilio/menu`);
      }
    } else {
      twiml.say(
        { voice: lang.voice, language: lang.langCode },
        lang.invalidOption
      );
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
  public static async recordSpeech(req: Request, res: Response) {
    const twiml = new twilio.twiml.VoiceResponse();
    const sessionId = (req.body.CallSid || req.query.CallSid || 'test-session') as string;
    const transcript = (req.body.SpeechResult || req.query.SpeechResult) as string;

    const session = sessionManager.getOrCreate(sessionId);
    const lang = resources[session.language];

    sessionManager.logAction(sessionId, `Speech recognized: "${transcript}"`);

    if (!transcript) {
      twiml.say(
        { voice: lang.voice, language: lang.langCode },
        lang.noInput
      );
      twiml.redirect(`${getPublicUrl()}/twilio/menu`);
      res.type('text/xml');
      return res.send(twiml.toString());
    }

    // Update session state with the transcript
    sessionManager.update(sessionId, {
      previousTranscript: transcript,
    });

    try {
      twiml.say(
        { voice: lang.voice, language: lang.langCode },
        lang.processing
      );

      // Call downstream AI API
      const result = await BackendService.query(transcript, sessionId);

      // Cache the answer
      sessionManager.update(sessionId, {
        previousAnswer: result.answer,
      });

      // Play the answer wrapped in a Gather, so they can interrupt by pressing 6 (or any key)
      const playGather = twiml.gather({
        numDigits: 1,
        action: `${getPublicUrl()}/twilio/menu-select`,
        method: 'POST',
        timeout: 4,
      });

      playGather.say(
        { voice: lang.voice, language: lang.langCode },
        `${result.answer}.`
      );

      // If they listen to the whole answer without pressing a key
      twiml.redirect(`${getPublicUrl()}/twilio/menu`);
    } catch (error) {
      console.error('Error fetching AI answer:', error);
      twiml.say(
        { voice: lang.voice, language: lang.langCode },
        lang.error
      );
      twiml.redirect(`${getPublicUrl()}/twilio/menu`);
    }

    res.type('text/xml');
    res.send(twiml.toString());
  }
}
