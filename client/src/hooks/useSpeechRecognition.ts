/**
 * Speech recognition hook using Web Speech API
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAppStore } from '../store/appStore';

interface SpeechRecognitionEvent extends Event {
    results: SpeechRecognitionResultList;
    resultIndex: number;
}

interface SpeechRecognitionResultList {
    length: number;
    item(index: number): SpeechRecognitionResult;
    [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
    isFinal: boolean;
    length: number;
    item(index: number): SpeechRecognitionAlternative;
    [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
    transcript: string;
    confidence: number;
}

interface SpeechRecognition extends EventTarget {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    start(): void;
    stop(): void;
    abort(): void;
    onresult: ((event: SpeechRecognitionEvent) => void) | null;
    onerror: ((event: Event) => void) | null;
    onend: (() => void) | null;
    onstart: (() => void) | null;
}

declare global {
    interface Window {
        SpeechRecognition: new () => SpeechRecognition;
        webkitSpeechRecognition: new () => SpeechRecognition;
    }
}

export function useSpeechRecognition(onTranscript: (text: string, isFinal: boolean) => void) {
    const recognitionRef = useRef<SpeechRecognition | null>(null);
    const [isSupported, setIsSupported] = useState(true);
    const [interimTranscript, setInterimTranscript] = useState('');

    const { isRecording, setRecording } = useAppStore();

    // Initialize speech recognition
    useEffect(() => {
        const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognitionClass) {
            console.warn('Speech recognition not supported in this browser');
            setIsSupported(false);
            return;
        }

        const recognition = new SpeechRecognitionClass();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event: SpeechRecognitionEvent) => {
            let interim = '';
            let final = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    final += result[0].transcript;
                } else {
                    interim += result[0].transcript;
                }
            }

            if (interim) {
                setInterimTranscript(interim);
            }

            if (final) {
                setInterimTranscript('');
                onTranscript(final.trim(), true);
            }
        };

        recognition.onerror = (event: Event) => {
            console.error('Speech recognition error:', event);
            setRecording(false);
        };

        recognition.onend = () => {
            // Restart if still recording
            if (useAppStore.getState().isRecording) {
                try {
                    recognition.start();
                } catch (e) {
                    console.warn('Failed to restart recognition:', e);
                }
            }
        };

        recognitionRef.current = recognition;

        return () => {
            recognition.abort();
        };
    }, [onTranscript, setRecording]);

    // Start recording
    const startRecording = useCallback(() => {
        if (!recognitionRef.current || !isSupported) {
            console.error('Speech recognition not available');
            return;
        }

        try {
            recognitionRef.current.start();
            setRecording(true);
            setInterimTranscript('');
        } catch (error) {
            console.error('Failed to start recording:', error);
        }
    }, [isSupported, setRecording]);

    // Stop recording
    const stopRecording = useCallback(() => {
        if (recognitionRef.current) {
            recognitionRef.current.stop();
        }
        setRecording(false);
        setInterimTranscript('');
    }, [setRecording]);

    // Toggle recording
    const toggleRecording = useCallback(() => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    }, [isRecording, startRecording, stopRecording]);

    return {
        isSupported,
        isRecording,
        interimTranscript,
        startRecording,
        stopRecording,
        toggleRecording,
    };
}
