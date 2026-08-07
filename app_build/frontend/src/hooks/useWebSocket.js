/**
 * useWebSocket.js — Custom React Hook for Nyaya-Dhwani Audio WebSocket
 *
 * Manages the persistent WebSocket connection to ws://localhost:8000/ws/audio
 * and exposes a one-shot send-and-receive function for audio processing.
 *
 * v3.0 WebSocket Contract (spec §3.2 / §3.3):
 *   AUDIO_RESPONSE  → decode audio_b64 → Web Audio API playback
 *   TTS_FALLBACK    → window.speechSynthesis.speak(), surfaces isTtsFallback=true
 *
 * ZERO MOCK DATA: no hardcoded audio or text. Errors propagate to the caller.
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
        if (!pendingResolveRef.current) return;

        try {
          const data = JSON.parse(event.data);

          // ─────────────────────────────────────────────────────────────
          // AUDIO_RESPONSE (spec §3.2 step 12)
          // Backend synthesised audio successfully via ElevenLabs.
          // Decode Base64 → play via Web Audio API.
          // ─────────────────────────────────────────────────────────────
          if (data.action === 'AUDIO_RESPONSE') {
            if (data.audio_b64 && data.audio_b64.length > 0) {
              try {
                const audio = new Audio('data:audio/mp3;base64,' + data.audio_b64);
                audio.play().catch(e => console.error('[useWebSocket] Audio playback error:', e));
              } catch (audioErr) {
                console.error('[useWebSocket] Failed to construct Audio:', audioErr);
              }
            }
            // Resolve with the full response payload for state update
            pendingResolveRef.current({ ...data, isTtsFallback: false });

          // ─────────────────────────────────────────────────────────────
          // TTS_FALLBACK (spec §3.3)
          // ElevenLabs is unavailable. No audio_b64 is present.
          // Trigger browser native SpeechSynthesis and surface the
          // fallback flag so App.jsx can show the warning indicator.
          // ─────────────────────────────────────────────────────────────
          } else if (data.action === 'TTS_FALLBACK') {
            try {
              // Cancel any currently speaking utterance before starting a new one
              window.speechSynthesis.cancel();
              const utterance = new SpeechSynthesisUtterance(data.text);
              utterance.lang = 'hi-IN';
              utterance.onerror = (e) => console.error('[useWebSocket] SpeechSynthesis error:', e);
              window.speechSynthesis.speak(utterance);
            } catch (speechErr) {
              console.error('[useWebSocket] SpeechSynthesis fallback error:', speechErr);
            }
            // Resolve with isTtsFallback=true so App.jsx shows the indicator
            pendingResolveRef.current({ ...data, isTtsFallback: true });

          // ─────────────────────────────────────────────────────────────
          // Error from backend (bad payload, STT failure, etc.)
          // ─────────────────────────────────────────────────────────────
          } else if (data.error) {
            pendingRejectRef.current(new Error(data.error));

          // ─────────────────────────────────────────────────────────────
          // Other backend messages (e.g., connection acknowledgements)
          // ─────────────────────────────────────────────────────────────
          } else {
            pendingResolveRef.current(data);
          }

        } catch (e) {
          pendingRejectRef.current(new Error('Failed to parse WebSocket response'));
        }

        // Clear pending refs after each resolved/rejected message
        pendingResolveRef.current = null;
        pendingRejectRef.current = null;
      };
    });
  }, []);

  /**
   * Sends Base64-encoded audio for processing and awaits the response.
   * JSON format: {"action": "PROCESS_AUDIO", "audio_b64": "<base64>", "phone_hash": "..."}
   *
   * Resolves with the full ActionResponse payload plus:
   *   - isTtsFallback: boolean — true if SpeechSynthesis was used instead of ElevenLabs
   *
   * @param {string} phoneHash - Caller identifier
   * @param {string} audioBase64 - Base64-encoded audio blob (from FileReader.readAsDataURL)
   * @returns {Promise<Object>} - ActionResponse from the backend
   */
  const sendAudio = useCallback(async (phoneHash, audioBase64) => {
    const ws = await connect();

    return new Promise((resolve, reject) => {
      // Store refs before setting up the timeout-clearing wrapper
      pendingRejectRef.current = reject;

      const timeoutId = setTimeout(() => {
        if (pendingRejectRef.current) {
          pendingRejectRef.current(new Error('Audio processing timed out (45s). The pipeline may still be running.'));
          pendingResolveRef.current = null;
          pendingRejectRef.current = null;
        }
      }, 45000);

      // Wrap resolve to clear the timeout when the message arrives
      pendingResolveRef.current = (value) => {
        clearTimeout(timeoutId);
        resolve(value);
      };

      ws.send(JSON.stringify({
        action: 'PROCESS_AUDIO',
        audio_b64: audioBase64,
        phone_hash: phoneHash
      }));
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
