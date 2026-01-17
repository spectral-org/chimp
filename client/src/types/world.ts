/**
 * Type definitions for world state and WebSocket messages
 */

// Intent types
export type IntentType =
    | 'buy_item'
    | 'negotiate'
    | 'ask_info'
    | 'give_item'
    | 'move'
    | 'interact'
    | 'greet'
    | 'unknown';

// Grammar types
export type Tense = 'present' | 'past' | 'conditional' | 'future';
export type Politeness = 'neutral' | 'polite' | 'rude';
export type NPCMood = 'friendly' | 'neutral' | 'annoyed' | 'angry';

// Action schema
export interface GrammarFeatures {
    tense: Tense;
    politeness: Politeness;
    required_constructs_present: string[];
}

export interface ActionEntities {
    item: string | null;
    quantity: number | null;
    target: string | null;
}

export interface ParsedAction {
    intent: IntentType;
    entities: ActionEntities;
    grammar_features: GrammarFeatures;
    confidence: number;
    canonical_transcript: string;
    feedback_keys: string[];
}

// World state
export interface NPCState {
    id: string;
    name: string;
    role: string;
    position: [number, number, number];
    mood: NPCMood;
    inventory: Record<string, number>;
    patience: number;
    dialogue_history: string[];
}

export interface PlayerState {
    position: [number, number, number];
    inventory: Record<string, number>;
    gold: number;
    reputation: number;
}

export interface MissionState {
    id: string;
    title: string;
    description: string;
    grammar_requirement: string;
    success_condition: string;
    is_complete: boolean;
    attempts: number;
}

export interface WorldState {
    timestamp: string;
    player: PlayerState;
    npcs: NPCState[];
    current_mission: MissionState | null;
    completed_missions: string[];
    world_time: 'morning' | 'afternoon' | 'evening' | 'night';
}

// WebSocket messages
export interface TranscriptMessage {
    type: 'transcript';
    text: string;
    is_final: boolean;
}

export interface ActionResultMessage {
    type: 'action_result';
    parsed_action: ParsedAction;
    validation_passed: boolean;
    feedback: string[];
    world_diff: WorldDiff;
}

export interface WorldStateMessage {
    type: 'world_state';
    state: WorldState;
}

export interface ReasoningChainMessage {
    type: 'reasoning';
    agent: string;
    step: string;
    details: Record<string, unknown>;
}

export interface ErrorMessage {
    type: 'error';
    message: string;
    recoverable: boolean;
}

export interface NPCAudioMessage {
    type: 'npc_audio';
    audio_data: string;  // Base64-encoded MP3
    npc_name: string;
    dialogue: string;
    mood: string;
}

export interface WorldDiff {
    player_changes: Record<string, unknown>;
    npc_changes: Record<string, Record<string, unknown>>;
    mission_changes: Record<string, unknown>;
    npc_dialogue: string | null;
    world_event: string | null;
}

export type ServerMessage =
    | TranscriptMessage
    | ActionResultMessage
    | WorldStateMessage
    | ReasoningChainMessage
    | ErrorMessage
    | NPCAudioMessage
    | { type: 'pong' };

// Transcript entry for UI
export interface TranscriptEntry {
    id: string;
    type: 'player' | 'npc' | 'system' | 'feedback';
    text: string;
    timestamp: Date;
}

// Reasoning step for visibility panel
export interface ReasoningStep {
    id: string;
    agent: string;
    step: string;
    details: Record<string, unknown>;
    timestamp: Date;
}
