import React, { useEffect } from 'react';
import { useAudioStream } from './hooks/useAudioStream';
import { useSimulationSocket } from './hooks/useSimulationSocket';
import { World } from './components/World';

const WS_URL = 'ws://127.0.0.1:8000/ws/simulation';

function App() {
  // Connect to Socket
  const { isConnected, worldState, feedback, sendAudio, sendJSON } = useSimulationSocket(WS_URL);

  // Connect Audio Stream to Socket Sender
  const { isRecording, startRecording, stopRecording } = useAudioStream(sendAudio);

  // Keyboard shortcut for PTT (Hold Space)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !isRecording && !e.repeat) {
        startRecording();
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space' && isRecording) {
        stopRecording();
        sendJSON({ type: "commit" });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [isRecording, startRecording, stopRecording]);

  return (
    <>
      <div className="ui-overlay">
        <div className="status-badge" style={{ color: isConnected ? '#4caf50' : '#f44336' }}>
          {isConnected ? 'LIVE' : 'DISCONNECTED'}
        </div>

        <div className="transcript-box">
          {isRecording ? "Listening..." : "Hold SPACE to speak"}
        </div>

        {feedback && (
          <div className="feedback-box">
            {feedback}
          </div>
        )}
      </div>

      <World gameState={worldState} />
    </>
  );
}

export default App;
