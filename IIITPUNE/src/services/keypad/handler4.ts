import { registerHandler } from './register';
import { BackendService } from '../backendService';
import { sessionManager } from '../sessionManager';
import { resources } from '../../utils/langResources';

registerHandler('4', async (context) => {
  const { twiml, session, sessionId, publicUrl } = context;
  const lang = resources[session.language];

  if (!session.previousAnswer) {
    twiml.say(
      { voice: lang.voice, language: lang.langCode },
      lang.noPreviousAnswer
    );
    twiml.redirect(`${publicUrl}/twilio/menu`);
    return;
  }

  try {
    twiml.say(
      { voice: lang.voice, language: lang.langCode },
      lang.simplifying
    );

    const result = await BackendService.simplify(session.previousAnswer, sessionId);
    
    // Play simplified answer
    twiml.say(
      { voice: lang.voice, language: lang.langCode },
      result.answer
    );

    // Update session state
    sessionManager.update(sessionId, {
      previousAnswer: result.answer,
    });
    sessionManager.logAction(sessionId, `Simplified previous response to: "${result.answer}"`);
  } catch (error) {
    console.error('Error during simplify:', error);
    twiml.say(
      { voice: lang.voice, language: lang.langCode },
      lang.simplifyError
    );
  }

  // Redirect back to main menu
  twiml.redirect(`${publicUrl}/twilio/menu`);
});
