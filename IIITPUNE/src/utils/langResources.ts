export interface LangResource {
  voice: any;
  langCode: any;
  welcome: string;
  menuOptions: string;
  recordingPrompt: string;
  noInput: string;
  error: string;
  stopped: string;
  processing: string;
  invalidOption: string;
  noPreviousAnswer: string;
  repeating: string;
  simplifying: string;
  simplifyError: string;
  followupPrompt: string;
  noFollowups: string;
  followupError: string;
}

export const resources: Record<'en' | 'hi', LangResource> = {
  en: {
    voice: 'Polly.Aditi',
    langCode: 'en-IN',
    welcome: 'Welcome to NyayaSathi. This is an AI legal information assistant. This service provides legal information, not legal advice.',
    menuOptions: 'Press 1 to ask a new question. Press 3 to repeat the previous answer. Press 4 to simplify the previous answer. Press 5 to hear suggested follow-up questions. Press 6 to stop the current response.',
    recordingPrompt: 'Please ask your question now. You can press the hash key or stop speaking when you are done.',
    noInput: "We did not receive any input. Returning to the main menu.",
    error: 'Sorry, the legal assistant is currently unavailable. Please try again later.',
    stopped: 'Speech stopped. Returning to the main menu.',
    processing: 'Processing your question. Please wait.',
    invalidOption: 'Invalid input. Please choose a valid menu option.',
    noPreviousAnswer: 'There is no previous response to repeat.',
    repeating: 'Repeating the previous answer: ',
    simplifying: 'Simplifying the answer, please wait.',
    simplifyError: 'Sorry, we could not simplify the response at this moment.',
    followupPrompt: 'Here are some suggested follow up questions you can ask:',
    noFollowups: 'No follow up questions are available at this time.',
    followupError: 'Sorry, we could not retrieve follow up questions at this time.'
  },
  hi: {
    voice: 'Polly.Aditi',  // Polly.Aditi is bilingual (English + Hindi)
    langCode: 'hi-IN',
    welcome: 'न्यायसाथी में आपका स्वागत है। यह एक एआई कानूनी सूचना सहायक है। यह सेवा केवल कानूनी जानकारी प्रदान करती है, कानूनी सलाह नहीं।',
    menuOptions: 'नया प्रश्न पूछने के लिए 1 दबाएं। पिछला उत्तर दोहराने के लिए 3 दबाएं। पिछले उत्तर को सरल बताने के लिए 4 दबाएं। सुझाए गए अनुवर्ती प्रश्न सुनने के लिए 5 दबाएं। वर्तमान उत्तर को रोकने के लिए 6 दबाएं।',
    recordingPrompt: 'कृपया अपना प्रश्न अभी पूछें। समाप्त होने पर आप हैश दबा सकते हैं या बोलना बंद कर सकते हैं।',
    noInput: "हमें कोई इनपुट नहीं मिला। मुख्य मेनू पर वापस जा रहे हैं।",
    error: 'क्षमा करें, कानूनी सहायक इस समय उपलब्ध नहीं है। कृपया बाद में पुनः प्रयास करें।',
    stopped: 'आवाज़ बंद कर दी गई है। मुख्य मेनू पर वापस जा रहे हैं।',
    processing: 'आपके प्रश्न पर काम किया जा रहा है। कृपया प्रतीक्षा करें।',
    invalidOption: 'अमान्य इनपुट। कृपया एक मान्य मेनू विकल्प चुनें।',
    noPreviousAnswer: 'दौहराने के लिए कोई पिछला उत्तर उपलब्ध नहीं है।',
    repeating: 'पिछला उत्तर दोहराया जा रहा है: ',
    simplifying: 'उत्तर को सरल बनाया जा रहा है, कृपया प्रतीक्षा करें।',
    simplifyError: 'क्षमा करें, हम इस समय उत्तर को सरल नहीं बना सके।',
    followupPrompt: 'यहाँ कुछ सुझाए गए अनुवर्ती प्रश्न दिए गए हैं जिन्हें आप पूछ सकते हैं:',
    noFollowups: 'इस समय कोई अनुवर्ती प्रश्न उपलब्ध हैं।',
    followupError: 'क्षमा करें, हम इस समय अनुवर्ती प्रश्न प्राप्त नहीं कर सके।'
  }
};
