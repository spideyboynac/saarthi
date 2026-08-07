/**
 * Nyaya-Dhwani API Client — v2.1 (NO MOCK DATA)
 * 
 * Enforcement 1: ALL mock response functions have been DELETED.
 * Enforcement 3: Action 2 sends audio via WebSocket as Base64.
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
 */
export async function sendAudioForProcessing(phoneHash, audioBase64) {
  const ws = await getAudioWebSocket();

  return new Promise((resolve, reject) => {
    // Set up one-shot message handler for this request
    const handler = (event) => {
      ws.removeEventListener('message', handler);
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          reject(new Error(data.error));
        } else {
          resolve(data);
        }
      } catch (e) {
        reject(new Error('Failed to parse WebSocket response'));
      }
    };

    ws.addEventListener('message', handler);

    // Enforcement 3: Exact JSON format as specified
    ws.send(JSON.stringify({
      action: "PROCESS_AUDIO",
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
