/**
 * UI Components for the medieval bazaar overlay
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useAppStore } from '../store/appStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';

// Header with connection status
export function Header() {
    const isConnected = useAppStore((state) => state.isConnected);
    const worldState = useAppStore((state) => state.worldState);

    return (
        <header className="header">
            <h1>🏰 Medieval Bazaar</h1>
            <div className="status">
                <span>{worldState?.world_time || 'morning'}</span>
                <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
                <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
        </header>
    );
}

// Mission panel
export function MissionPanel() {
    const mission = useAppStore((state) => state.mission);

    if (!mission) {
        return (
            <div className="mission-panel">
                <h2>📜 Loading mission...</h2>
            </div>
        );
    }

    return (
        <div className="mission-panel">
            <h2>📜 {mission.title}</h2>
            <p className="description">{mission.description}</p>
            <div className="requirement">
                <strong>Grammar focus:</strong> {mission.grammar_requirement}
            </div>
        </div>
    );
}

// Player stats panel
export function PlayerStats() {
    const worldState = useAppStore((state) => state.worldState);
    const player = worldState?.player;

    if (!player) return null;

    return (
        <div className="player-stats">
            <h3>👤 Traveler</h3>
            <div className="stat-row">
                <span className="label">Gold:</span>
                <span className="value gold">💰 {player.gold}</span>
            </div>
            <div className="stat-row">
                <span className="label">Reputation:</span>
                <span className="value">{(player.reputation * 100).toFixed(0)}%</span>
            </div>
            {Object.keys(player.inventory).length > 0 && (
                <div className="inventory-grid">
                    {Object.entries(player.inventory).map(([item, count]) => (
                        <span key={item} className="inventory-item">
                            {item}: {count}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
}

// Transcript panel
export function TranscriptPanel() {
    const transcripts = useAppStore((state) => state.transcripts);
    const panelRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (panelRef.current) {
            panelRef.current.scrollTop = panelRef.current.scrollHeight;
        }
    }, [transcripts]);

    if (transcripts.length === 0) {
        return (
            <div className="transcript-panel" ref={panelRef}>
                <div className="transcript-entry system">
                    Welcome to the Medieval Bazaar! Speak or type to interact with merchants.
                </div>
            </div>
        );
    }

    return (
        <div className="transcript-panel" ref={panelRef}>
            {transcripts.map((entry) => (
                <div key={entry.id} className={`transcript-entry ${entry.type}`}>
                    {entry.type === 'player' && <strong>You: </strong>}
                    {entry.type === 'npc' && <strong>Merchant: </strong>}
                    {entry.text}
                </div>
            ))}
        </div>
    );
}

// Reasoning chain panel (for visibility)
export function ReasoningPanel() {
    const reasoningChain = useAppStore((state) => state.reasoningChain);

    if (reasoningChain.length === 0) return null;

    return (
        <div className="reasoning-panel">
            <h3>🧠 Agent Reasoning</h3>
            {reasoningChain.map((step) => (
                <div key={step.id} className="reasoning-step">
                    <span className="agent">[{step.agent}]</span> {step.step}
                    {step.details.output && (
                        <div className="details">
                            {JSON.stringify(step.details.output, null, 0).substring(0, 100)}...
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

// Text input for typing messages
export function TextInput() {
    const [text, setText] = useState('');
    const { sendTranscript } = useWebSocket();
    const isConnected = useAppStore((state) => state.isConnected);
    const addTranscript = useAppStore((state) => state.addTranscript);

    const handleSubmit = useCallback((e: React.FormEvent) => {
        e.preventDefault();
        if (text.trim() && isConnected) {
            addTranscript({ type: 'player', text: text.trim() });
            sendTranscript(text.trim());
            setText('');
        }
    }, [text, isConnected, sendTranscript, addTranscript]);

    return (
        <form className="text-input-container" onSubmit={handleSubmit}>
            <input
                type="text"
                className="text-input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Type your message or speak..."
                disabled={!isConnected}
            />
            <button
                type="submit"
                className="send-button"
                disabled={!isConnected || !text.trim()}
            >
                Send
            </button>
        </form>
    );
}

// Microphone button with speech recognition
export function MicrophoneButton() {
    const { sendTranscript } = useWebSocket();
    const addTranscript = useAppStore((state) => state.addTranscript);

    const handleTranscript = useCallback((text: string, isFinal: boolean) => {
        if (isFinal && text.trim()) {
            addTranscript({ type: 'player', text: text.trim() });
            sendTranscript(text.trim());
        }
    }, [sendTranscript, addTranscript]);

    const {
        isSupported,
        isRecording,
        interimTranscript,
        toggleRecording
    } = useSpeechRecognition(handleTranscript);

    if (!isSupported) {
        return null; // Don't show mic button if not supported
    }

    return (
        <div className="mic-container">
            <button
                className={`mic-button ${isRecording ? 'recording' : ''}`}
                onClick={toggleRecording}
                title={isRecording ? 'Stop recording' : 'Start recording'}
            >
                {isRecording ? '⏹️' : '🎤'}
            </button>
            <span className="mic-hint">
                {isRecording
                    ? (interimTranscript || 'Listening...')
                    : 'Click to speak'}
            </span>
        </div>
    );
}

// NPC Dialogue bubble
export function NPCDialogue() {
    const npcDialogue = useAppStore((state) => state.npcDialogue);

    if (!npcDialogue) return null;

    return (
        <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            background: 'rgba(26, 26, 46, 0.95)',
            border: '3px solid #d4af37',
            borderRadius: '16px',
            padding: '20px 30px',
            maxWidth: '400px',
            textAlign: 'center',
            fontSize: '1.1rem',
            color: '#f4e4bc',
            pointerEvents: 'none',
            animation: 'fadeIn 0.3s ease',
        }}>
            <strong>Merchant says:</strong>
            <p style={{ marginTop: '10px' }}>{npcDialogue}</p>
        </div>
    );
}
