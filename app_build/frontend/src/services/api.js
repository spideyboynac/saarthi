/**
 * Nyaya-Dhwani API Client — v3.0 (ZERO MOCK DATA)
 *
 * v3.0 WebSocket Contract:
 *   AUDIO_RESPONSE  → decode audio_b64 → Web Audio API playback
 *   TTS_FALLBACK    → window.speechSynthesis.speak(), isTtsFallback=true
 *
 * Audio path:  getUserMedia → MediaRecorder → Blob → Base64 → WebSocket
 * Other actions: REST POST /api/v1/query/action
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';
const WS_AUDIO_URL = 'ws://localhost:8000/ws/audio';

let _ws = null;
let _wsResolve = null;

/**
 * Returns a connected WebSocket to /ws/audio.
 * Reuses an existing connection if still open.
 */
function getAudioWebSocket() {
  return new Promise((resolve, reject) => {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      resolve(_ws);
      return;
    }

    _ws = new WebSocket(WS_AUDIO_URL);

    _ws.onopen = () => {
      console.log('[WS] Connected to /ws/audio');
      resolve(_ws);
    };

    _ws.onerror = (err) => {
      console.error('[WS] Connection error:', err);
      reject(new Error('WebSocket connection to backend failed. Is the server running?'));
    };

    _ws.onclose = () => {
      console.warn('[WS] Disconnected from /ws/audio');
      _ws = null;
    };
  });
}

/**
 * Sends Base64-encoded audio over WebSocket and waits for the response.
 * Exact JSON format: {"action": "PROCESS_AUDIO", "audio_b64": "<base64_string>"}
 *
 * Resolves with the full ActionResponse payload plus:
 *   isTtsFallback: boolean — true if SpeechSynthesis was used instead of ElevenLabs
 */
export async function sendAudioForProcessing(phoneHash, audioBase64) {
  const ws = await getAudioWebSocket();

  return new Promise((resolve, reject) => {
    // Set up one-shot message handler for this request
    const handler = (event) => {
      ws.removeEventListener('message', handler);
      try {
        const data = JSON.parse(event.data);

        // ───────────────────────────────────────────────────────────────
        // AUDIO_RESPONSE (spec §3.2 step 12)
        // ElevenLabs TTS succeeded. Decode audio_b64 → Web Audio playback.
        // ───────────────────────────────────────────────────────────────
        if (data.action === 'AUDIO_RESPONSE') {
          if (data.audio_b64 && data.audio_b64.length > 0) {
            try {
              const audio = new Audio('data:audio/mp3;base64,' + data.audio_b64);
              audio.play().catch(e => console.error('[api.js] Audio playback error:', e));
            } catch (audioErr) {
              console.error('[api.js] Failed to construct Audio:', audioErr);
            }
          }
          resolve({ ...data, isTtsFallback: false });

        // ───────────────────────────────────────────────────────────────
        // TTS_FALLBACK (spec §3.3)
        // ElevenLabs is unavailable — no audio_b64 field present.
        // Trigger browser native SpeechSynthesis.
        // ───────────────────────────────────────────────────────────────
        } else if (data.action === 'TTS_FALLBACK') {
          try {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(data.text);
            utterance.lang = 'hi-IN';
            utterance.onerror = (e) => console.error('[api.js] SpeechSynthesis error:', e);
            window.speechSynthesis.speak(utterance);
          } catch (speechErr) {
            console.error('[api.js] SpeechSynthesis fallback error:', speechErr);
          }
          resolve({ ...data, isTtsFallback: true });

        } else if (data.error) {
          reject(new Error(data.error));
        } else {
          resolve(data);
        }
      } catch (e) {
        reject(new Error('Failed to parse WebSocket response'));
      }
    };

    ws.addEventListener('message', handler);

    // Spec §3.2 step 3: exact JSON format
    ws.send(JSON.stringify({
      action: 'PROCESS_AUDIO',
      audio_b64: audioBase64,
      phone_hash: phoneHash
    }));
  });
}

/**
 * Sends non-audio actions (3, 4, 5, 6) via REST POST.
 * NO MOCK FALLBACK — if backend is unreachable, throws an error.
 */
export async function sendAction(phoneHash, actionCode, payload = null) {
  const res = await fetch(`${API_BASE_URL}/query/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phone_hash: phoneHash,
      action_code: actionCode,
      payload: payload
    })
  });

  if (!res.ok) {
    throw new Error(`Backend returned HTTP ${res.status}. Ensure the server is running on port 8000.`);
  }

  return await res.json();
}

/**
 * Fetches session state. NO MOCK FALLBACK.
 */
export async function fetchSession(phoneHash) {
  const res = await fetch(`${API_BASE_URL}/query/session/${phoneHash}`);

  if (!res.ok) {
    throw new Error(`Failed to fetch session: HTTP ${res.status}`);
  }

  return await res.json();
}
