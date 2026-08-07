# Project Architecture — Team Build Reference

**Problem statements:** PS07 (Human-Centered AI for Rural Communities) — primary. PS04 (Legal Literacy Conversational Agent) — secondary, integrated.

**One-line pitch:** A voice-first, multilingual legal-literacy assistant that works over a phone call in low-network areas, refuses to guess when unsure, and adapts its explanation to how well each caller understood the last one.

---

## 1. Model Stack

| Component | Model | Why |
|---|---|---|
| Speech-to-text | IndicASR / IndicWav2Vec | Tuned for Indian accents (SeamlessM4T tested weaker here) |
| Translation | IndicTrans2 (211M) + legal glossary layer | Native ↔ English; glossary layer corrects legal-specific terms translation alone misses |
| Retrieval embedding | bge-large-en-v1.5 | English-only; fine since translation layer normalizes input |
| Reranker | MS-MARCO-MiniLM-L-6-v2 | Cross-encoder; reference paper measured Precision@5 0.71→0.89 with this addition |
| Generation (offline) | Llama 3.1 8B, Q4_K_M via Ollama, base instruct | ~5-6GB VRAM, fits 4-6GB GPU laptop; RAG-grounded, no fine-tuning (see §8b) |
| Generation (online) | Claude API | Cloud escalation tier, better reasoning when available |
| Text-to-speech | ElevenLabs | Cloud-only — best quality, but breaks offline chain for voice specifically |
| Vector store | FAISS or Chroma | Local, one index per legal document for targeted retrieval |
| Call infrastructure | Twilio | Record, Gather (DTMF), Play — works on any phone, no app needed |

## 2. Full Pipeline (see diagram above for the core 6 stages)

**Detailed steps:**
1. Query arrives (phone call, app, or web) — voice or text
2. First-time caller: onboarding disclaimer plays once ("I know about laws, I'm not a lawyer")
3. If voice: IndicASR converts native-language speech → text
4. Intent classifier: legal vs. non-legal — reject off-topic immediately, no wasted compute
5. Connectivity check: route to local (Ollama) or cloud (Claude); queue query if mid-switch
6. IndicTrans2: query → English
7. bge-large-en-v1.5 embeds query → retrieves top-20 from **both** vector indices (Legal Knowledge RAG + Case Example RAG, per §8b) based on intent-classifier routing
8. Cross-encoder reranks combined candidates → top-5
9. Relevance-check loop: if LLM judges the context insufficient, refine query and re-retrieve (bounded retries)
10. Confidence check:
    - Strong match → generate answer
    - Weak/ambiguous → ask a clarifying (Socratic) follow-up question
    - No usable match → refuse + human/legal-aid handoff, with a structured summary of the conversation so far
11. LLM generates English answer — grounded only in retrieved text, descriptive language only ("the law states X," never "you should X"), at the caller's current literacy tier
12. IndicTrans2: English → native language
13. Output delivered: text with confidence indicator + source citation ("where is this from?"), or voice via ElevenLabs TTS
14. Voice/call mode: numpad controls available throughout, including mid-playback (barge-in) — see §3 for the full control map

## 3. Phone Call Flow (Twilio) — Tier 3 access path

1. User dials in → brief greeting explains the controls
2. Numpad 1 → begin recording (`<Record>` starts)
3. Numpad 2 → end recording (`<Record finishOnKey="2">`), query submitted for processing
4. Hold message plays while the pipeline runs (covers round-trip latency)
5. Answer plays via `<Play>` nested inside `<Gather>`, so any keypress interrupts playback immediately (barge-in) — the caller is never stuck waiting out a response they don't need
6. Numpad controls, live throughout and during playback:

| Key | Action |
|---|---|
| 1 | Ask new question — starts voice input |
| 2 | Voice input over — stops recording, submits query |
| 3 | Repeat last answer — replays `last_answer_text`, no regeneration |
| 4 | Didn't understand — simplify `last_answer_text` via a dedicated simplify prompt, no RAG re-run (see §4) |
| 5 | Recommend follow-up questions — generated from `last_answer_text` via a dedicated prompt, no RAG re-run (same pattern as key 4) |
| 6 | Stop current response immediately |
| 0 | Human handoff (standard IVR convention, retained) |

Recorded audio is processed through our own IndicASR, not Twilio's built-in speech-to-text — Twilio's STT has the same weak Indian-accent handling documented for SeamlessM4T.

## 4. Literacy Scoring & Session State

Keyed by Twilio's `From` number, **hashed before storage** (privacy — don't store raw phone numbers).

```
user_profile: { phone_hash, current_tier, reexplain_count, total_calls, last_updated }
call_session: { phone_hash, last_answer_text, last_answer_tier, call_active }
```

`call_session` is per-call, in-memory or short-TTL storage — it only needs to survive for the duration of the current call, unlike `user_profile` which persists long-term.

- New caller starts at **Standard** tier (3 tiers: Simple / Standard / Detailed — matches Arapai's validated tiered-explanation pattern, condensed for voice)
- Key 4 ("didn't understand") → **does not re-run retrieval or generation from scratch.** It sends `last_answer_text` back to the LLM with a separate, narrow system prompt ("rewrite this answer in simpler language, same facts, no new claims") and no RAG involved — the original retrieved passages already grounded the first answer, so simplifying it can't introduce new hallucinated content the way a fresh generation could
- Key 5 ("recommend follow-up questions") follows the same pattern — `last_answer_text` goes to the LLM with a "suggest 2-3 natural follow-up questions a caller might ask next" prompt, no retrieval involved, since the follow-ups only need to relate to what was just said, not new legal facts
- This also drops the caller's tier by one for the rest of the call and persists that as their new default next time
- Several clean calls (no key-4 presses) → tier creeps back up slowly, not after one call

## 5. Feature List (full)

**Trust & safety:** confidence display · refuse-if-low-confidence · ask-before-answering until contextual clearance (Socratic questioning) · source/citation traceability · descriptive-not-prescriptive language guardrail · human/legal-aid escalation with structured handoff · uncertainty markers · correction/feedback loop

**Accessibility:** multilingual via translation layer · voice-first + pictogram fallback for core actions · step-wise output formatting · large touch targets · persona/tone selector · first-run onboarding · code-mixing tolerance · phone-call access (no smartphone needed) · barge-in (interrupt playback mid-response, any time)

**Resilience:** hybrid offline/online auto-switch · query queuing during switch · session continuity across drops · local caching of common queries (offline floor) · per-caller literacy adaptation

**Guidance:** prompt enhancer · suggestive follow-up questions (voice-accessible via key 5) · repeat-last-answer on demand · progressive prompting literacy (teaches user over repeat use)

**Retrieval quality:** two-stage retrieval (broad + rerank) · hybrid dense+BM25 · iterative relevance-check/query-refinement loop · per-document indices · 512-token/64-overlap chunking · retrieval scoped to new questions only (keys 1/2) — repeat, simplify, and follow-up-suggestion actions (keys 3/4/5) work off the cached last answer, no re-retrieval or fresh generation

## 6. Connectivity / Access Tiers

| Tier | Path | Needs internet? |
|---|---|---|
| 1 | Cloud (Claude), smartphone/app | Yes |
| 2 | Local community server (laptop/mini-PC) broadcasting WiFi hotspot, phones connect locally | No |
| 3 | Phone call via Twilio (built) + cached FAQ floor (design fallback) | Twilio needs backend internet; caller needs none |

## 7. Data Pipeline

- Scope: 2-3 narrow legal topics for a working demo (not full corpus) — broader coverage described as extensible in the case study
- Sources: official government portals only (IndiaCode, legislative.gov.in) — primary, public-domain text
- Perplexity used for source discovery (Acts, case law, academic articles, official FAQs, common misconceptions)
- No training/fine-tuning — RAG only; legal knowledge lives in retrieved documents, not model weights

## 8b. Dual-RAG & Terminology Adaptation

**Decision: no fine-tuning.** Every research paper we reviewed that worked (Mina, Indian Law LLM, JurisAI) used RAG on a base model, not a fine-tuned one — the one fine-tuned Indian-legal model we found on Hugging Face was trained under 1 epoch on free compute and is a cautionary example, not a template. Fine-tuning under hackathon time pressure risks degrading the base model's instruction-following for no proven gain. RAG-only is the evidence-backed choice.

**Dual-RAG:** two separate vector indices —
- **Legal Knowledge RAG** — statutes, Acts, government schemes, official FAQs (existing pipeline, §1 ingestion)
- **Case Example RAG** — real judgments / simplified case examples, built the same way as the knowledge index but from a separate case-law corpus

The intent classifier (pipeline step 4) is extended to also tag query type (pure statute lookup vs. "has this happened before" style question) and routes retrieval to one or both indices. Both branches' top candidates are merged before reranking (one shared reranker, one shared "answer only from this retrieved text" prompt — no architecture duplication beyond the second index).

**Translation layer:** a legal glossary/terminology-adjustment layer sits alongside IndicTrans2 (same pattern as Mina's Legal Dictionary tool) — catches legal-specific terms that generic translation training data under-represents, before/after the translation pass.

## 8. Team Roles (4-person parallel tracks)

1. **Data & knowledge base** — gather/clean legal docs, chunk, build vector DB
2. **Offline model + RAG logic** — Ollama setup, retrieval/rerank wiring, confidence check, relevance-refinement loop
3. **Cloud integration + switching + Twilio** — Claude API, connectivity detection, query queue, call flow, literacy scoring
4. **Interface/UX** — voice input, confidence UI, pictograms, multilingual toggle, escalation UI, onboarding

## 9. Roadmap

- **Pre-hackathon (2+ weeks):** gather legal data, install/test local stack, sketch UX flow, build mini RAG proof-of-concept, test Twilio sandbox
- **Hackathon (24h):** 0-4h skeleton integration → 4-14h parallel build → 14-18h full integration → 18-22h polish demo path (2-3 rehearsed example queries/calls) → 22-24h pitch deck + rehearsal

## 10. Known Limitations (state these honestly, don't hide them)

- Single-context-window RAG struggles with reasoning across multiple statutes at once
- ElevenLabs TTS requires internet — voice output unavailable in fully offline mode
- Corpus scoped narrow for demo; full coverage is future work
- Twilio call latency stacks across 4+ processing hops — hold message is a mitigation, not a fix
- Twilio free tier is demo-only; real deployment has per-minute cost

## 11. Research Grounding (for case study citations)

- **Mina** (Bangladesh legal assistant) — RAG architecture, two-stage retrieval, error analysis on hallucination/conflation risk; explicitly names the clarification-policy gap as future work — we built it
- **Arapai** — offline-first tiered-explanation pattern (Simple → Technical), hardware-aware model selection
- **Indian Law LLM** — cross-encoder reranker validated (0.71→0.89 Precision@5), intent classifier, CPU-only feasibility
- **JurisAI** — iterative relevance-check loop, hybrid dense+BM25 retrieval
- **BharatLex** — cautionary example: verbatim accuracy ≠ plain-language usefulness; informs dual-mode output design
- **VideoKheti, Avaaj Otalo, FarmChat** — HCI4D precedent for voice/multimodal rural design
- **UX gap-analysis doc** — Socratic questioning framing, pictogram patterns, guardrail language, escalation-as-social-scaffold framing
- **Fine-tuning risk assessment** — cross-referenced against all reference papers (none fine-tuned their generation model) plus a hobbyist Indian-legal fine-tune on Hugging Face (under 1 epoch, cautionary) as the basis for choosing dual-RAG over fine-tuning
