import { registerHandler } from './register';
import { sessionManager } from '../sessionManager';
import { resources } from '../../utils/langResources';

registerHandler('6', (context) => {
  const { twiml, session, sessionId, publicUrl } = context;
  const lang = resources[session.language];

  sessionManager.logAction(sessionId, 'Interrupted and stopped playback.');

  twiml.say(
    { voice: lang.voice, language: lang.langCode },
    lang.stopped
  );

  twiml.redirect(`${publicUrl}/twilio/menu`);
});
