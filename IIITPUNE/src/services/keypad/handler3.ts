import { registerHandler } from './register';
import { resources } from '../../utils/langResources';

registerHandler('3', (context) => {
  const { twiml, session, publicUrl } = context;
  const lang = resources[session.language];

  if (session.previousAnswer) {
    twiml.say(
      { voice: lang.voice, language: lang.langCode },
      `${lang.repeating}${session.previousAnswer}`
    );
  } else {
    twiml.say(
      { voice: lang.voice, language: lang.langCode },
      lang.noPreviousAnswer
    );
  }

  // Redirect back to main menu
  twiml.redirect(`${publicUrl}/twilio/menu`);
});
