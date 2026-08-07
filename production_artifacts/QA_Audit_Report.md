# 🔍 QA Audit Report — Nyaya-Dhwani v2.1 Hardcoding Eradication Sweep

> **Auditor**: QA Engineer (@qa)  
> **Date**: 2026-08-07  
> **Verdict**: ✅ **PASS — All hardcoded mock data eradicated**

---

## 1. Audit Scope

Full forensic scan of `app_build/frontend/` and `app_build/backend/` for:
- Exact phrase: `"What are my legal rights regarding unpaid salary"`
- Any hardcoded English legal question used as a fallback or mock payload
- WebSocket `ws.send()` transmitting anything other than `audio_b64` from MediaRecorder

---

## 2. Bugs Found & Fixed

### 🔴 BUG-001: Hardcoded Legal Question in STT Dev Stub (CRITICAL)

**File**: `backend/app/services/stt_service.py` (line 63-64)

**Problem**: The STT development transcription stub was injecting a fabricated English legal question:
```python
# ❌ BEFORE — fabricated legal query injected into RAG pipeline
f"User spoke a legal query via browser microphone. "
f"What are the steps to file a complaint at the consumer court?"
```

**Fix**: Replaced with metadata-only output containing no legal content:
```python
# ✅ AFTER — audio metadata only, no fabricated query
f"Transcription pending — real STT engine (IndicASR) required for production."
```

---

### 🔴 BUG-002: Hardcoded Fallback in Action 4 (Simplify) (CRITICAL)

**File**: `backend/app/services/action_handler.py` (line 83)

**Problem**: When `session.last_answer_text` was empty, Action 4 fell back to a hardcoded English legal string:
```python
# ❌ BEFORE
last_text = session.last_answer_text or "You have rights under Indian Law."
```

**Fix**: Replaced with neutral system instruction:
```python
# ✅ AFTER
last_text = session.last_answer_text or "[No prior answer in session — ask a question first using Action 1]"
```

---

### 🔴 BUG-003: Hardcoded Fallback in Action 5 (Follow-Ups) (CRITICAL)

**File**: `backend/app/services/action_handler.py` (line 113)

**Problem**: Same pattern — fabricated legal content when session was empty:
```python
# ❌ BEFORE
last_text = session.last_answer_text or "Regarding worker compensation and unpaid wages."
```

**Fix**: Replaced with neutral system instruction:
```python
# ✅ AFTER
last_text = session.last_answer_text or "[No prior answer in session — ask a question first using Action 1]"
```

---

## 3. WebSocket `ws.send()` Verification

| File | Line | Payload Transmitted | Verdict |
|---|---|---|---|
| `hooks/useWebSocket.js` | 85 | `{action: "PROCESS_AUDIO", audio_b64: audioBase64, phone_hash}` | ✅ **Clean** |
| `services/api.js` | 73 | `{action: "PROCESS_AUDIO", audio_b64: audioBase64, phone_hash}` | ✅ **Clean** |

**Result**: Both `ws.send()` calls transmit ONLY the `audio_b64` payload from MediaRecorder. No hardcoded text, no mock strings, no fabricated queries.

---

## 4. Post-Fix Sweep Results

| Search Query | Matches Found | Status |
|---|---|---|
| `"What are my legal rights regarding unpaid salary"` | 0 | ✅ Clean |
| `"What are my legal rights"` | 0 | ✅ Clean |
| `"What are the steps to file"` | 0 | ✅ Clean |
| `"User spoke a legal query"` | 0 | ✅ Clean |
| `"You have rights under Indian"` | 0 | ✅ Clean |
| `"unpaid wages"` (as fallback) | 0 | ✅ Clean |
| `"wage dispute"` | 0 | ✅ Clean |
| `"delayed wages"` | 0 | ✅ Clean |
| `getMockResponse` | 0 | ✅ Clean |

---

## 5. Test Suite Verification (11/11 Pass)

```
Ran 11 tests in 4.254s — OK
```

All enforcement tests pass, including:
- `test_03b`: Confirms Action 1/2 raises `ValueError` on empty payload
- `test_08`: Confirms STT decodes real Base64 audio bytes
- `test_09`: Confirms STT strips data-URI prefix
- `test_10`: Confirms STT flags audio that is too short

---

## 6. Final Verdict

> **✅ ALL CLEAR — Zero hardcoded mock legal text remains in the codebase.**
> 
> The only remaining legal text in the codebase exists in:
> - `rag_service.py` — RAG knowledge base corpus entries (legitimate)
> - `action_handler.py:119-124` — Socratic follow-up suggestions (system-generated, not user-input mocks)
> - `run_tests.py:28` — Test payload deliberately simulating real transcription input (correct test behavior)
