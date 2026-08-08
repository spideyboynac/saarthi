import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import ActionGrid from './components/ActionGrid';
import AudioVisualizer from './components/AudioVisualizer';
import ResponseCard from './components/ResponseCard';
import { sendAction, fetchSession } from './services/api';
import useWebSocket from './hooks/useWebSocket';
import './App.css';

export default function App() {
  const [phoneHash] = useState('demo-phone-user-101');
  const [llmRoute, setLlmRoute] = useState('CLAUDE_CLOUD');
  const [literacyTier, setLiteracyTier] = useState('STANDARD');
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentResponse, setCurrentResponse] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  // TTS fallback indicator — true when SpeechSynthesis is active (spec §3.3)
  const [nativeTtsActive, setNativeTtsActive] = useState(false);

  // Real microphone refs (Enforcement 2)
  const mediaStreamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const analyserRef = useRef(null);

  // WebSocket hook for audio transport (Enforcement 3)
  const { sendAudio } = useWebSocket();

  // Load initial session state
  useEffect(() => {
    async function initSession() {
      try {
        const data = await fetchSession(phoneHash);
        if (data && data.call_session) {
          setLiteracyTier(data.call_session.last_answer_tier || 'STANDARD');
          if (data.call_session.last_answer_text) {
            setCurrentResponse({
              action_name: "Active Call Session",
              question: data.call_session.last_question,
              answer_text: data.call_session.last_answer_text,
              sources: data.call_session.last_sources || [],
              literacy_tier: data.call_session.last_answer_tier,
              rag_executed: false,
              llm_route: data.llm_route || 'OLLAMA_LOCAL'
            });
          }
        }
        if (data && data.llm_route) {
          setLlmRoute(data.llm_route);
        }
        setErrorMessage(null);
      } catch (err) {
        setErrorMessage(`Backend unavailable: ${err.message}`);
      }
    }
    initSession();
  }, [phoneHash]);

  // Cleanup media stream on unmount
  useEffect(() => {
    return () => {
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  // =========================================================
  // ACTION 1: Start recording — NATIVE BROWSER MIC
  // Enforcement 2: navigator.mediaDevices.getUserMedia
  // =========================================================
  const startRecording = async () => {
    setErrorMessage(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];

      // Create AnalyserNode for real waveform data
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Create MediaRecorder to capture audio chunks
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.start(250); // Collect chunks every 250ms
      setIsRecording(true);
      setIsPlaying(false);
    } catch (err) {
      setErrorMessage(`Microphone access denied: ${err.message}. Please allow microphone permissions.`);
    }
  };

  // =========================================================
  // ACTION 2: Stop recording → Base64 encode → WebSocket send
  // Enforcement 3: Blob → Base64 → {"action": "PROCESS_AUDIO", "audio_b64": "..."}
  // =========================================================
  const stopRecordingAndSubmit = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === 'inactive') {
      setErrorMessage('No active recording to submit. Press Action 1 first.');
      return;
    }

    setIsRecording(false);
    setIsProcessing(true);
    setErrorMessage(null);

    recorder.onstop = async () => {
      // Stop all microphone tracks
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(t => t.stop());
        mediaStreamRef.current = null;
      }
      analyserRef.current = null;

      // Assemble chunks into a single Blob
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm;codecs=opus' });
      audioChunksRef.current = [];

      if (audioBlob.size < 100) {
        setErrorMessage('Recording too short. Please speak clearly and try again.');
        setIsProcessing(false);
        return;
      }

      // Convert Blob → Base64 string using FileReader
      const reader = new FileReader();
      reader.onloadend = async () => {
        const audioBase64 = reader.result; // 'data:audio/webm;codecs=opus;base64,...'

        try {
          // Send over WebSocket via useWebSocket hook
          const res = await sendAudio(phoneHash, audioBase64);
          setCurrentResponse({
            action_name: res.action_name || "New Question / Input Over",
            question: res.question,
            answer_text: res.text || res.answer_text,
            sources: res.sources || [],
            literacy_tier: res.literacy_tier,
            rag_executed: res.rag_executed,
            llm_route: res.llm_route,
            socratic_followups: res.socratic_followups
          });
          setLiteracyTier(res.literacy_tier);
          setLlmRoute(res.llm_route);
          setIsPlaying(true);
          // v3.0 spec §3.3: surface native TTS indicator if ElevenLabs was unavailable
          setNativeTtsActive(res.isTtsFallback === true);
        } catch (err) {
          setErrorMessage(`Audio processing failed: ${err.message}`);
        } finally {
          setIsProcessing(false);
        }
      };
      reader.readAsDataURL(audioBlob);
    };

    recorder.stop();
  };

  // =========================================================
  // Master 6-Action Handler
  // =========================================================
  const handleAction = async (actionCode) => {
    setErrorMessage(null);

    // Action 1: Start microphone recording
    if (actionCode === 1) {
      await startRecording();
      return;
    }

    // Action 2: Stop recording & send audio via WebSocket
    if (actionCode === 2) {
      stopRecordingAndSubmit();
      return;
    }

    // Action 6: Barge-in stop
    if (actionCode === 6) {
      setIsRecording(false);
      setIsPlaying(false);
      setNativeTtsActive(false);
      // Cancel any active SpeechSynthesis utterance (spec §3.3)
      window.speechSynthesis.cancel();
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(t => t.stop());
        mediaStreamRef.current = null;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      try {
        const res = await sendAction(phoneHash, 6);
        setCurrentResponse(res);
      } catch (err) {
        setErrorMessage(`Action failed: ${err.message}`);
      }
      return;
    }

    // Actions 3, 4, 5: REST API (no audio involved in request, but audio returned in response)
    setIsRecording(false);
    setIsPlaying(true);
    setNativeTtsActive(false);
    try {
      const res = await sendAction(phoneHash, actionCode);
      setCurrentResponse(res);
      setLiteracyTier(res.literacy_tier);
      if (res.llm_route !== "NONE" && !res.llm_route.includes("REPLAY")) {
        setLlmRoute(res.llm_route);
      }

      // Play audio response if returned by backend (ElevenLabs b64 or SpeechSynthesis fallback)
      if (res.audio_b64 && res.audio_b64.length > 0) {
        try {
          window.speechSynthesis.cancel();
          const audio = new Audio('data:audio/mp3;base64,' + res.audio_b64);
          audio.onended = () => setIsPlaying(false);
          audio.onerror = () => setIsPlaying(false);
          await audio.play();
        } catch (audioErr) {
          console.error('[App.jsx] Audio playback error:', audioErr);
          setIsPlaying(false);
        }
      } else if (res.answer_text) {
        try {
          window.speechSynthesis.cancel();
          setNativeTtsActive(true);
          const utterance = new SpeechSynthesisUtterance(res.answer_text);
          utterance.lang = 'en-IN';
          utterance.onend = () => {
            setIsPlaying(false);
            setNativeTtsActive(false);
          };
          utterance.onerror = () => {
            setIsPlaying(false);
            setNativeTtsActive(false);
          };
          window.speechSynthesis.speak(utterance);
        } catch (speechErr) {
          console.error('[App.jsx] SpeechSynthesis error:', speechErr);
          setIsPlaying(false);
        }
      } else {
        setIsPlaying(false);
      }
    } catch (err) {
      setIsPlaying(false);
      setErrorMessage(`Action failed: ${err.message}`);
    }
  };

  const handleSelectFollowup = async (questionText) => {
    setErrorMessage(null);
    setIsPlaying(true);
    try {
      // Follow-up questions are text-based, sent directly via REST as Action 2 payload
      const res = await sendAction(phoneHash, 2, questionText);
      setCurrentResponse(res);
      setLiteracyTier(res.literacy_tier);
      setLlmRoute(res.llm_route);

      // Play audio response for selected follow-up question
      if (res.audio_b64 && res.audio_b64.length > 0) {
        try {
          window.speechSynthesis.cancel();
          const audio = new Audio('data:audio/mp3;base64,' + res.audio_b64);
          audio.onended = () => setIsPlaying(false);
          audio.onerror = () => setIsPlaying(false);
          await audio.play();
        } catch (audioErr) {
          console.error('[App.jsx] Audio playback error:', audioErr);
          setIsPlaying(false);
        }
      } else if (res.answer_text) {
        try {
          window.speechSynthesis.cancel();
          setNativeTtsActive(true);
          const utterance = new SpeechSynthesisUtterance(res.answer_text);
          utterance.lang = 'en-IN';
          utterance.onend = () => {
            setIsPlaying(false);
            setNativeTtsActive(false);
          };
          utterance.onerror = () => {
            setIsPlaying(false);
            setNativeTtsActive(false);
          };
          window.speechSynthesis.speak(utterance);
        } catch (speechErr) {
          console.error('[App.jsx] SpeechSynthesis error:', speechErr);
          setIsPlaying(false);
        }
      } else {
        setIsPlaying(false);
      }
    } catch (err) {
      setIsPlaying(false);
      setErrorMessage(`Follow-up failed: ${err.message}`);
    }
  };

  return (
    <div className="app-container">
      {/* Live Status Header */}
      <Header
        llmRoute={llmRoute}
        literacyTier={literacyTier}
        isRecording={isRecording}
      />

      {/* Error Banner */}
      {errorMessage && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          <span>{errorMessage}</span>
          <button className="error-dismiss" onClick={() => setErrorMessage(null)}>✕</button>
        </div>
      )}

      {/* Native TTS Fallback Warning (spec §3.3) */}
      {nativeTtsActive && (
        <div className="tts-fallback-banner">
          <span>🔊 Using device voice (ElevenLabs unavailable)</span>
          <button className="error-dismiss" onClick={() => {
            window.speechSynthesis.cancel();
            setNativeTtsActive(false);
          }}>✕</button>
        </div>
      )}

      {/* Processing Indicator */}
      {isProcessing && (
        <div className="processing-banner">
          <span className="spinner"></span>
          <span>Decoding audio & processing through Dual-RAG pipeline...</span>
        </div>
      )}

      {/* Audio Waveform Visualizer (connected to real AnalyserNode) */}
      <AudioVisualizer
        isRecording={isRecording}
        isPlaying={isPlaying}
        analyserNode={analyserRef.current}
      />

      {/* 6-Action Massive Pictogram Grid (120px height) */}
      <ActionGrid
        onActionTrigger={handleAction}
        isRecording={isRecording}
        isPlaying={isPlaying}
      />

      {/* Legal Response & Socratic Follow-ups Card */}
      <ResponseCard
        response={currentResponse}
        onSelectFollowup={handleSelectFollowup}
      />
    </div>
  );
}
