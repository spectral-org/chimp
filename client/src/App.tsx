/**
 * Main App Component
 * Combines 3D world with UI overlay
 */

import { useEffect } from 'react';
import { World } from './components/World';
import {
    Header,
    MissionPanel,
    PlayerStats,
    TranscriptPanel,
    ReasoningPanel,
    TextInput,
    MicrophoneButton,
    NPCDialogue
} from './components/UI';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
    const { connect } = useWebSocket();

    useEffect(() => {
        // Connect on mount
        connect();
    }, [connect]);

    return (
        <div className="app-container">
            {/* 3D World */}
            <World />

            {/* UI Overlay */}
            <div className="ui-overlay">
                {/* Top bar */}
                <Header />

                {/* Mission panel (top-left) */}
                <MissionPanel />

                {/* Player stats (below mission) */}
                <PlayerStats />

                {/* Reasoning chain (top-right) */}
                <ReasoningPanel />

                {/* NPC Dialogue bubble */}
                <NPCDialogue />

                {/* Transcript panel (bottom) */}
                <TranscriptPanel />

                {/* Input area */}
                <TextInput />

                {/* Microphone button (overlaid on text input) */}
                <div style={{
                    position: 'absolute',
                    bottom: '20px',
                    right: '20px',
                }}>
                    <MicrophoneButton />
                </div>
            </div>
        </div>
    );
}

export default App;
