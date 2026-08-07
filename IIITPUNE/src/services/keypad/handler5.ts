import { registerHandler } from './register';
import { BackendService } from '../backendService';
import { sessionManager } from '../sessionManager';
import { resources } from '../../utils/langResources';

registerHandler('5', async (context) => {
  const { twiml, session, sessionId, publicUrl } = context;
  const lang = resources[session.language];

  try {
    const result = await BackendService.getFollowups(sessionId);
    
    if (result.questions && result.questions.length > 0) {
      twiml.say(
        { voice: lang.voice, language: lang.langCode },
        lang.followupPrompt
      );
      
      result.questions.forEach((q, index) => {
        twiml.say(
          { voice: lang.voice, language: lang.langCode },
          `Option ${index + 1}: ${q}`
        );
      });
      sessionManager.logAction(sessionId, `Read followups: ${JSON.stringify(result.questions)}`);
    } else {
      twiml.say(
        { voice: lang.voice, language: lang.langCode },
        lang.noFollowups
      );
    }
  } catch (error) {
    console.error('Error fetching followups:', error);
    twiml.say(
      { voice: lang.voice, language: lang.langCode },
      lang.followupError
    );
  }

  // Redirect back to main menu
  twiml.redirect(`${publicUrl}/twilio/menu`);
});
