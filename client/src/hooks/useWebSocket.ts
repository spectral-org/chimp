/**
 * WebSocket hook for real-time communication with backend
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAppStore } from '../store/appStore';
import type { ServerMessage } from '../types/world';

const WS_URL = (import.meta as unknown as { env: { DEV: boolean } }).env.DEV
    ? 'ws://localhost:8000/ws'
    : `wss://${window.location.host}/ws`;

export function useWebSocket() {
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<number>();
    const [isReconnecting, setIsReconnecting] = useState(false);

    const {
        sessionId,
        setSessionId,
        setConnected,
        setWorldState,
        addTranscript,
        addReasoningStep,
        clearReasoningChain,
        setLastAction,
        setNpcDialogue,
    } = useAppStore();

    // Create new session
    const createSession = useCallback(async () => {
        try {
            const response = await fetch('/api/session', { method: 'POST' });
            const data = await response.json();
            return data.session_id;
        } catch (error) {
            console.error('Failed to create session:', error);
            // Generate local session ID as fallback
            return `local-${Math.random().toString(36).substring(2, 9)}`;
        }
    }, []);

    // Connect to WebSocket
    const connect = useCallback(async () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        let sid = sessionId;
        if (!sid) {
            sid = await createSession();
            setSessionId(sid);
        }

        console.log(`[WS] Connecting to ${WS_URL}/${sid}`);

        const ws = new WebSocket(`${WS_URL}/${sid}`);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('[WS] Connected');
            setConnected(true);
            setIsReconnecting(false);
        };

        ws.onmessage = (event) => {
            try {
                const message: ServerMessage = JSON.parse(event.data);
                handleMessage(message);
            } catch (error) {
                console.error('[WS] Failed to parse message:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('[WS] Error:', error);
        };

        ws.onclose = () => {
            console.log('[WS] Disconnected');
            setConnected(false);

            // Auto-reconnect after 3 seconds
            if (!isReconnecting) {
                setIsReconnecting(true);
                reconnectTimeoutRef.current = window.setTimeout(() => {
                    console.log('[WS] Attempting reconnect...');
                    connect();
                }, 3000);
            }
        };
    }, [sessionId, createSession, setSessionId, setConnected, isReconnecting]);

    // Handle incoming messages
    const handleMessage = useCallback((message: ServerMessage) => {
        console.log('[WS] Received:', message.type, message);

        switch (message.type) {
            case 'world_state':
                setWorldState(message.state);
                break;

            case 'transcript':
                if (message.text) {
                    addTranscript({
                        type: 'player',
                        text: message.text,
                    });
                }
                break;

            case 'action_result':
                setLastAction(message.parsed_action, message.feedback);

                // Add NPC dialogue to transcript
                if (message.world_diff?.npc_dialogue) {
                    setNpcDialogue(message.world_diff.npc_dialogue);
                    addTranscript({
                        type: 'npc',
                        text: message.world_diff.npc_dialogue,
                    });
                }

                // Add world event
                if (message.world_diff?.world_event) {
                    addTranscript({
                        type: 'system',
                        text: message.world_diff.world_event,
                    });
                }

                // Add feedback
                message.feedback.forEach(fb => {
                    addTranscript({
                        type: 'feedback',
                        text: fb,
                    });
                });
                break;

            case 'reasoning':
                addReasoningStep({
                    agent: message.agent,
                    step: message.step,
                    details: message.details,
                });
                break;

            case 'npc_audio':
                // Play NPC voice audio (base64 WAV from Gemini TTS)
                if (message.audio_data) {
                    try {
                        const audioBlob = new Blob(
                            [Uint8Array.from(atob(message.audio_data), c => c.charCodeAt(0))],
                            { type: 'audio/wav' }
                        );
                        const audioUrl = URL.createObjectURL(audioBlob);
                        const audio = new Audio(audioUrl);
                        audio.onended = () => URL.revokeObjectURL(audioUrl);
                        audio.play().catch(err => console.error('[Audio] Playback error:', err));
                        console.log(`[Audio] Playing NPC voice (${message.mood})`);
                    } catch (err) {
                        console.error('[Audio] Failed to play NPC audio:', err);
                    }
                }
                break;

            case 'error':
                console.error('[WS] Server error:', message.message);
                addTranscript({
                    type: 'system',
                    text: `Error: ${message.message}`,
                });
                break;

            case 'pong':
                // Heartbeat response
                break;
        }
    }, [setWorldState, addTranscript, addReasoningStep, setLastAction, setNpcDialogue]);

    // Send transcript to server
    const sendTranscript = useCallback((text: string, isFinal: boolean = true) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
            console.error('[WS] Not connected');
            return;
        }

        // Clear reasoning chain for new interaction
        if (isFinal) {
            clearReasoningChain();
        }

        wsRef.current.send(JSON.stringify({
            type: 'transcript',
            text,
            is_final: isFinal,
        }));
    }, [clearReasoningChain]);

    // Send ping
    const sendPing = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }));
        }
    }, []);

    // Disconnect
    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setConnected(false);
    }, [setConnected]);

    // Auto-connect on mount
    useEffect(() => {
        connect();

        // Heartbeat every 30 seconds
        const heartbeat = setInterval(sendPing, 30000);

        return () => {
            clearInterval(heartbeat);
            disconnect();
        };
    }, []);

    return {
        connect,
        disconnect,
        sendTranscript,
        isConnected: useAppStore.getState().isConnected,
    };
}
