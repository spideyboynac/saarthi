# Nyaya-Dhwani (Saarthi): Legal Literacy Agent

## 1. Summary
Nyaya-Dhwani (Saarthi) is a voice-first, dual-access legal literacy assistant designed to bridge the justice gap in India. It empowers users to ask complex legal questions in their native language and receive grounded, accurate, and simplified answers based on both statutory law and case precedents. Designed with a strict "CORE ACCESS MODEL," the system is equally accessible via a standard phone call (for offline users) and a rich mobile web app (for online users)—ensuring that connectivity and literacy are no longer barriers to understanding one's legal rights.

## 2. The Problem
Access to legal literacy in rural India faces compounding barriers:
*   **Connectivity & Hardware:** Many individuals do not own smartphones or have access to reliable high-speed data.
*   **Literacy & Language:** Complex legal jargon is inaccessible, and state-specific laws are often unavailable in regional dialects or audio formats.
*   **Cost & Trust:** Professional legal help is prohibitively expensive, and hallucinating AI chatbots are too dangerous to trust with critical legal inquiries.

## 3. How It Works — The Two Access Paths
To solve this, Nyaya-Dhwani uses a unified backend that serves two distinct user interfaces, guaranteeing the same quality of legal retrieval and safety guardrails regardless of how the user connects:

*   **Path 1: The Phone Call (Offline/Low-Tech)**
    Users *without* a smartphone or internet data plan simply dial a standard phone number **(+1 234-956-2135)** powered by Twilio. There is no app to download. They speak their question naturally, and the system responds with a spoken, easy-to-understand answer. *(Note: For this hackathon prototype, the phone line is only live while the local backend server and an expose tunnel like ngrok are running. In production, this runs on a persistent cloud server).*
    
    *Walkthrough:* 
    1. User dials **+1 234-956-2135**. 
    2. Prompted by a greeting, the user asks their legal question by voice. 
    3. The system processes the audio, retrieves legal statutes and case precedents, checks confidence, and generates an answer. 
    4. The user hears the spoken response and can use their phone's keypad to navigate follow-ups (e.g., press `4` to simplify, `1` to ask something new).

*   **Path 2: The Web App (Online/High-Tech)**
    Users *with* a smartphone and internet access use the React-based web app. They get the exact same backend RAG and LLM logic, but enhanced with a richer visual UI. The app displays text, actionable pictograms, and clickable follow-up suggestions on the screen alongside voice interaction.

## 4. Phone Call Controls
When interacting via the Twilio phone call path, users can navigate the conversation using standard numpad keys:

| Key | Action | Description |
| :--- | :--- | :--- |
| `1` | **New Question** | Starts a fresh query, clearing the current context. |
| `2` | **End Voice Input** | Signals the system to stop listening and process the audio. |
| `3` | **Repeat** | Repeats the last spoken answer. |
| `4` | **Simplify** | Re-explains the last answer in simpler terms. |
| `5` | **Suggest Follow-ups** | Suggests related questions the user might want to ask. |
| `6` | **Stop Response** | Interrupts the current spoken response. |
| `0` | **Human Handoff** | Connects the user to a human operator/legal aid. |

*Note: Keys 3, 4, and 5 respond instantly because they reuse the cached session context rather than re-triggering the full RAG search.*

## 5. Key Features
*   **Accessibility:** Multilingual support, voice-first interaction, standard phone line access, and literacy-adapted simplification (via keypad triggers).
*   **Trust & Safety:** A strict Confidence Engine scores retrieved context (High/Medium/Low). The system refuses to guess, asks Socratic clarifying questions if context is insufficient, cites sources, explicitly avoids giving prescriptive legal advice, and provides a trigger for human handoff (`0`).
*   **Resilience:** 
    *   *Hybrid LLM Routing:* Primary generation via Claude 3.5 Sonnet, with an automatic offline fallback to local Llama 3.1 8B (via Ollama) if the cloud API fails.
    *   *Dual Retrieval System:* Queries both statutory laws and real case precedents simultaneously using FAISS vector indices.

## 6. System Architecture
1.  **Speech-to-Text (ASR):** The user's spoken audio is streamed via Twilio and transcribed into text using Deepgram.
2.  **Retrieval-Augmented Generation (RAG):** The transcribed text is embedded (using `bge-large-en-v1.5`) and searched against two FAISS vector databases (Statutes and Cases).
3.  **Reranking & Confidence:** Results are reranked using `MS-MARCO-MiniLM-L-6-v2`. A confidence score is calculated. If the score is too low, the system refines the query or asks for clarification.
4.  **Answer Generation:** The LLM (Claude 3.5 or Llama 3.1) generates a grounded, cited response strictly based on the retrieved passages. 
5.  **Text-to-Speech (TTS):** The generated text is converted back to audio and streamed to the user over the Twilio call.

## 7. Tech Stack

| Component | Technology Used |
| :--- | :--- |
| **Backend Framework** | FastAPI (Python), Uvicorn |
| **Frontend Framework** | React (Vite), Lucide React |
| **Telephony & Audio** | Twilio API, Deepgram SDK |
| **LLM Routing** | Anthropic API (Claude), Ollama (Llama 3.1) |
| **Embeddings & Reranking**| `bge-large-en-v1.5`, `MS-MARCO-MiniLM-L-6-v2` |
| **Vector Store** | FAISS |

## 8. Setup and Running the Project

**Prerequisites:** Python 3.10+, Node.js, and an active Twilio/Deepgram/Anthropic account.

**1. Clone & Set Environment Variables**
Ensure your `.env` file in `app_build/backend/` is populated with `ANTHROPIC_API_KEY`, Twilio credentials, etc.

**2. Start the Backend (FastAPI)**
```bash
cd app_build/backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
*Note for Phone Path: To test the Twilio phone integration locally (via **+1 234-956-2135**), you must expose port 8000 using a tool like ngrok (`ngrok http 8000`) and point your Twilio Webhook to the ngrok URL.*

**3. Start the Frontend (React/Vite)**
```bash
cd app_build/frontend
npm install
npm run dev
```

## 9. Project Structure
```text
Saarthi/
├── app_build/
│   ├── backend/          # FastAPI server, Twilio routes, Hybrid LLM router
│   │   ├── app/
│   │   │   ├── api/      # REST endpoints (Twilio, SMS, Query)
│   │   │   ├── services/ # RAG core, Session management, Action handler
│   │   │   └── config.py # Environment & Model configurations
│   │   └── ...           # Test scripts and benchmarking tools
│   └── frontend/         # React application (Vite)
│       └── src/          # UI components, Hooks, API services
├── RAG/                  # RAG Hand-off docs and vector store indices
└── data/                 # Raw legal data and processing scripts
```

## 10. Current Scope and Honest Limitations
*   **Legal Scope:** The current vector database is populated with a subset of statutory laws and case precedents. It is not yet a comprehensive index of all Indian law.
*   **Telephony Environment:** Audio latency over Twilio depends on network conditions and the speed of the Deepgram/LLM APIs. Local testing via ngrok adds marginal delay compared to a deployed production server.
*   **Translation Pipeline:** While architected for multilingual support (via tools like Bhashini), the current end-to-end integration heavily relies on English for the RAG processing layer.
*   **Intent Classification:** The system currently queries both Statutes and Cases simultaneously. Upstream intent classification to route queries specifically to one index (for latency optimization) is architected but still under refinement.

## 11. Team and Acknowledgments
Built for Problem Statement **PS07** (Primary) and integrating elements of **PS04**. 
The dual-access architecture draws from research in accessible technology design for low-resource environments, prioritizing equitable legal empowerment for both offline and online users.
