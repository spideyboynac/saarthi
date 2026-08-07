import React, { useRef, useEffect } from 'react';

/**
 * AudioVisualizer — Enforcement 2 Compliant
 * 
 * Connects to a live AnalyserNode from the real MediaStream
 * to render actual waveform frequency data. No fake CSS bar
 * animations when recording.
 */
export default function AudioVisualizer({ isRecording, isPlaying, analyserNode }) {
  const canvasRef = useRef(null);
  const animationIdRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const WIDTH = canvas.width;
    const HEIGHT = canvas.height;

    // Clear any previous animation loop
    if (animationIdRef.current) {
      cancelAnimationFrame(animationIdRef.current);
      animationIdRef.current = null;
    }

    if (isRecording && analyserNode) {
      // REAL WAVEFORM: Draw live frequency data from AnalyserNode
      const bufferLength = analyserNode.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      const barWidth = (WIDTH / bufferLength) * 2.5;

      const draw = () => {
        animationIdRef.current = requestAnimationFrame(draw);
        analyserNode.getByteFrequencyData(dataArray);

        ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
        ctx.fillRect(0, 0, WIDTH, HEIGHT);

        let x = 0;
        for (let i = 0; i < bufferLength; i++) {
          const barHeight = (dataArray[i] / 255) * HEIGHT;
          
          // Gradient from blue to purple based on bar height
          const r = 96 + (dataArray[i] / 255) * 100;
          const g = 165 - (dataArray[i] / 255) * 80;
          const b = 246;
          ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
          ctx.fillRect(x, HEIGHT - barHeight, barWidth, barHeight);
          x += barWidth + 1;
        }
      };
      draw();
    } else {
      // IDLE / PLAYING STATE: Draw flat ambient bars
      ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
      ctx.fillRect(0, 0, WIDTH, HEIGHT);

      const barCount = 40;
      const barWidth = (WIDTH / barCount) - 2;
      for (let i = 0; i < barCount; i++) {
        const barHeight = isPlaying ? (Math.sin(i * 0.5) + 1) * 8 + 4 : 4;
        ctx.fillStyle = isPlaying ? 'rgba(96, 165, 246, 0.6)' : 'rgba(148, 163, 184, 0.3)';
        ctx.fillRect(i * (barWidth + 2), HEIGHT - barHeight, barWidth, barHeight);
      }
    }

    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
    };
  }, [isRecording, isPlaying, analyserNode]);

  return (
    <div className={`audio-visualizer-card ${isRecording ? 'mode-recording' : isPlaying ? 'mode-playing' : 'mode-idle'}`}>
      <div className="visualizer-status">
        <span className="mode-indicator">
          {isRecording ? '🎙️ CAPTURING LIVE MICROPHONE...' : isPlaying ? '🔊 SYNTHESIZING VOICE PLAYBACK...' : '🎧 VOICE STANDBY'}
        </span>
      </div>
      <canvas
        ref={canvasRef}
        width={600}
        height={60}
        className="waveform-canvas"
      />
    </div>
  );
}
