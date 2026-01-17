import { useEffect, useRef, useState, useCallback } from 'react';

export interface WorldState {
    timestamp: number;
    entities: Record<string, any>;
    mission_state: Record<string, any>;
}

export const useSimulationSocket = (url: string) => {
    const ws = useRef<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [worldState, setWorldState] = useState<WorldState | null>(null);
    const [feedback, setFeedback] = useState<string | null>(null);
    const [lastTranscript, setLastTranscript] = useState<string | null>(null);

    useEffect(() => {
        const socket = new WebSocket(url);
        ws.current = socket;

        socket.onopen = () => {
            console.log("Connected to Simulation Server");
            setIsConnected(true);
        };

        socket.onclose = () => {
            console.log("Disconnected from Simulation Server");
            setIsConnected(false);
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === "world_update") {
                    setWorldState(data.state);
                    if (data.feedback) setFeedback(data.feedback);
                    // Optionally update transcript if returned
                } else if (data.type === "agent_message") {
                    setFeedback(data.text);
                } else if (data.type === "error") {
                    console.error("Server Error:", data.message);
                }
            } catch (err) {
                console.error("Failed to parse message:", err);
            }
        };

        return () => {
            socket.close();
        };
    }, [url]);

    const sendAudio = useCallback((data: ArrayBuffer) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(data);
        }
    }, []);

    const sendMessage = useCallback((text: string) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ text }));
        }
    }, []);

    const sendJSON = useCallback((payload: any) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify(payload));
        }
    }, []);

    return { isConnected, worldState, feedback, lastTranscript, sendAudio, sendMessage, sendJSON };
};
