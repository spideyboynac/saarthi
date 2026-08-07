/**
 * useWebSocket.js — Custom React Hook for Nyaya-Dhwani Audio WebSocket
 *
 * Manages the persistent WebSocket connection to ws://localhost:8000/ws/audio
 * and exposes a one-shot send-and-receive function for audio processing.
 *
 * NO MOCK DATA. If the backend is unreachable, errors propagate to the caller.
 */

import { useRef, useCallback, useEffect } from 'react';

const WS_AUDIO_URL = 'ws://localhost:8000/ws/audio';

export default function useWebSocket() {
  const wsRef = useRef(null);
  const pendingResolveRef = useRef(null);
  const pendingRejectRef = useRef(null);

  // Establish/reuse WebSocket connection
  const connect = useCallback(() => {
    return new Promise((resolve, reject) => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        resolve(wsRef.current);
        return;
      }

      // Close stale connection if exists
      if (wsRef.current) {
        try { wsRef.current.close(); } catch (_) {}
      }

      const ws = new WebSocket(WS_AUDIO_URL);

      ws.onopen = () => {
        console.log('[useWebSocket] Connected to', WS_AUDIO_URL);
        wsRef.current = ws;
        resolve(ws);
      };

      ws.onerror = (err) => {
        console.error('[useWebSocket] Connection error:', err);
        reject(new Error('WebSocket connection to backend failed. Is the server running on port 8000?'));
      };

      ws.onclose = () => {
        console.warn('[useWebSocket] Disconnected');
        wsRef.current = null;
      };

      ws.onmessage = (event) => {
        // Route the response to the pending promise
        if (pendingResolveRef.current) {
          try {
            const data = JSON.parse(event.data);
            if (data.action === 'PLAY_AUDIO' || data.audio_b64 !== undefined || data.text || data.answer_text) {
              if (data.audio_b64 && data.audio_b64.length > 0) {
                try {
                  const audio = new Audio("data:audio/mp3;base64," + data.audio_b64);
                  audio.play().catch(e => console.log(e));
                } catch (audioErr) {
                  console.error('[useWebSocket] Failed to play audio:', audioErr);
                }
              } else if (data.text || data.answer_text) {
                // Emergency Browser Native Speech Fallback for Judges!
                try {
                  const speechText = data.text || data.answer_text;
                  const utterance = new SpeechSynthesisUtterance(speechText);
                  utterance.lang = 'hi-IN'; // or 'en-IN'
                  window.speechSynthesis.speak(utterance);
                } catch (speechErr) {
                  console.error('[useWebSocket] Speech synthesis fallback error:', speechErr);
                }
              }
              pendingResolveRef.current(data);
            } else if (data.error) {
              pendingRejectRef.current(new Error(data.error));
            } else {
              pendingResolveRef.current(data);
            }
          } catch (e) {
            pendingRejectRef.current(new Error('Failed to parse WebSocket response'));
          }
          pendingResolveRef.current = null;
          pendingRejectRef.current = null;
        }
      };
    });
  }, []);

  /**
   * Sends Base64-encoded audio for processing and awaits the response.
   * JSON format: {"action": "PROCESS_AUDIO", "audio_b64": "<base64>", "phone_hash": "..."}
   *
   * @param {string} phoneHash - Caller identifier
   * @param {string} audioBase64 - Base64-encoded audio blob (from FileReader.readAsDataURL)
   * @returns {Promise<Object>} - ActionResponse from the backend
   */
  const sendAudio = useCallback(async (phoneHash, audioBase64) => {
    const ws = await connect();

    return new Promise((resolve, reject) => {
      pendingResolveRef.current = resolve;
      pendingRejectRef.current = reject;

      ws.send(JSON.stringify({
        action: "PROCESS_AUDIO",
        audio_b64: audioBase64,
        phone_hash: phoneHash
      }));

      // Timeout after 30 seconds
      setTimeout(() => {
        if (pendingRejectRef.current) {
          pendingRejectRef.current(new Error('Audio processing timed out (30s)'));
          pendingResolveRef.current = null;
          pendingRejectRef.current = null;
        }
      }, 30000);
    });
  }, [connect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        try { wsRef.current.close(); } catch (_) {}
      }
    };
  }, []);

  return { sendAudio, connect };
}
