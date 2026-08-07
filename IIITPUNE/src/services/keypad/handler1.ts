import { registerHandler } from './register';
import { resources } from '../../utils/langResources';

registerHandler('1', (context) => {
  const { twiml, session, publicUrl } = context;
  const lang = resources[session.language];

  // Gather speech input using selected language voice & settings
  const gather = twiml.gather({
    input: ['speech', 'dtmf'],
    action: `${publicUrl}/twilio/record-speech`,
    method: 'POST',
    timeout: 5,
    speechTimeout: 'auto',
    finishOnKey: '#',
    language: lang.langCode, // Instruct Twilio to listen in the selected language!
  });

  gather.say(
    { voice: lang.voice, language: lang.langCode },
    lang.recordingPrompt
  );

  // If the user doesn't say anything
  twiml.say(
    { voice: lang.voice, language: lang.langCode },
    lang.noInput
  );
  twiml.redirect(`${publicUrl}/twilio/menu`);
});
