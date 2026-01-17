/**
 * Zustand store for global application state
 */

import { create } from 'zustand';
import type {
    WorldState,
    MissionState,
    TranscriptEntry,
    ReasoningStep,
    ParsedAction
} from '../types/world';

interface AppState {
    // Connection
    sessionId: string | null;
    isConnected: boolean;

    // World
    worldState: WorldState | null;
    mission: MissionState | null;

    // UI
    transcripts: TranscriptEntry[];
    reasoningChain: ReasoningStep[];
    lastAction: ParsedAction | null;
    lastFeedback: string[];
    npcDialogue: string | null;

    // Recording
    isRecording: boolean;

    // Actions
    setSessionId: (id: string) => void;
    setConnected: (connected: boolean) => void;
    setWorldState: (state: WorldState) => void;
    setMission: (mission: MissionState) => void;
    addTranscript: (entry: Omit<TranscriptEntry, 'id' | 'timestamp'>) => void;
    addReasoningStep: (step: Omit<ReasoningStep, 'id' | 'timestamp'>) => void;
    clearReasoningChain: () => void;
    setLastAction: (action: ParsedAction, feedback: string[]) => void;
    setNpcDialogue: (dialogue: string | null) => void;
    setRecording: (recording: boolean) => void;
    reset: () => void;
}

const generateId = () => Math.random().toString(36).substring(2, 9);

export const useAppStore = create<AppState>((set) => ({
    // Initial state
    sessionId: null,
    isConnected: false,
    worldState: null,
    mission: null,
    transcripts: [],
    reasoningChain: [],
    lastAction: null,
    lastFeedback: [],
    npcDialogue: null,
    isRecording: false,

    // Actions
    setSessionId: (id) => set({ sessionId: id }),

    setConnected: (connected) => set({ isConnected: connected }),

    setWorldState: (state) => set({
        worldState: state,
        mission: state.current_mission || null,
    }),

    setMission: (mission) => set({ mission }),

    addTranscript: (entry) => set((state) => ({
        transcripts: [
            ...state.transcripts.slice(-50), // Keep last 50
            {
                ...entry,
                id: generateId(),
                timestamp: new Date(),
            },
        ],
    })),

    addReasoningStep: (step) => set((state) => ({
        reasoningChain: [
            ...state.reasoningChain.slice(-20), // Keep last 20
            {
                ...step,
                id: generateId(),
                timestamp: new Date(),
            },
        ],
    })),

    clearReasoningChain: () => set({ reasoningChain: [] }),

    setLastAction: (action, feedback) => set({
        lastAction: action,
        lastFeedback: feedback,
    }),

    setNpcDialogue: (dialogue) => set({ npcDialogue: dialogue }),

    setRecording: (recording) => set({ isRecording: recording }),

    reset: () => set({
        sessionId: null,
        isConnected: false,
        worldState: null,
        mission: null,
        transcripts: [],
        reasoningChain: [],
        lastAction: null,
        lastFeedback: [],
        npcDialogue: null,
        isRecording: false,
    }),
}));
