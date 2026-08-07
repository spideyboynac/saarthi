import twilio from 'twilio';
import { SessionState } from '../sessionManager';

export interface KeypadContext {
  sessionId: string;
  session: SessionState;
  twiml: twilio.twiml.VoiceResponse;
  publicUrl: string;
}

export type KeypadHandler = (context: KeypadContext) => Promise<void> | void;

const registry: Record<string, KeypadHandler> = {};

export function registerHandler(key: string, handler: KeypadHandler) {
  registry[key] = handler;
}

export function getHandler(key: string): KeypadHandler | undefined {
  return registry[key];
}
