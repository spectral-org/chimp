/**
 * Medieval Bazaar 3D Scene
 * Three.js scene with React Three Fiber
 */

import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import {
    OrbitControls,
    Float,
    Sparkles,
} from '@react-three/drei';
import { useAppStore } from '../store/appStore';
import type * as THREE from 'three';

// Ground plane
function Ground() {
    return (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
            <planeGeometry args={[50, 50]} />
            <meshStandardMaterial color="#5a4a3a" roughness={0.9} />
        </mesh>
    );
}

// Market stall component
interface StallProps {
    position: [number, number, number];
    color: string;
    name: string;
    isActive?: boolean;
}

function Stall({ position, color, name: _name, isActive = false }: StallProps) {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((state) => {
        if (meshRef.current && isActive) {
            meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 2) * 0.05;
        }
    });

    return (
        <group position={position}>
            {/* Stall base */}
            <mesh ref={meshRef} position={[0, 0.5, 0]} castShadow>
                <boxGeometry args={[2, 1, 1.5]} />
                <meshStandardMaterial color={color} roughness={0.8} />
            </mesh>

            {/* Stall roof */}
            <mesh position={[0, 1.5, 0]} castShadow>
                <coneGeometry args={[1.5, 0.8, 4]} />
                <meshStandardMaterial color="#8b4513" roughness={0.7} />
            </mesh>

            {/* Items on display */}
            <group position={[0, 1.1, 0.5]}>
                {[...Array(5)].map((_, i) => (
                    <mesh key={i} position={[(i - 2) * 0.3, 0, 0]} castShadow>
                        <sphereGeometry args={[0.1, 8, 8]} />
                        <meshStandardMaterial color="#e74c3c" roughness={0.5} />
                    </mesh>
                ))}
            </group>

            {/* Active indicator */}
            {isActive && (
                <Sparkles
                    count={20}
                    scale={[2, 2, 2]}
                    position={[0, 1.5, 0]}
                    color="#d4af37"
                    size={3}
                />
            )}
        </group>
    );
}

// NPC component
interface NPCProps {
    position: [number, number, number];
    name: string;
    mood: 'friendly' | 'neutral' | 'annoyed' | 'angry';
    isActive?: boolean;
}

function NPC({ position, name: _name, mood, isActive = false }: NPCProps) {
    const meshRef = useRef<THREE.Mesh>(null);

    const moodColors: Record<string, string> = {
        friendly: '#27ae60',
        neutral: '#f39c12',
        annoyed: '#e67e22',
        angry: '#e74c3c',
    };

    useFrame((state) => {
        if (meshRef.current) {
            // Idle animation
            meshRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.1;
        }
    });

    return (
        <group position={position}>
            {/* Body */}
            <mesh ref={meshRef} position={[0, 0.7, 0]} castShadow>
                <capsuleGeometry args={[0.25, 0.7, 4, 8]} />
                <meshStandardMaterial color="#8d6e63" roughness={0.8} />
            </mesh>

            {/* Head */}
            <mesh position={[0, 1.3, 0]} castShadow>
                <sphereGeometry args={[0.2, 16, 16]} />
                <meshStandardMaterial color="#ffb74d" roughness={0.6} />
            </mesh>

            {/* Mood indicator */}
            <Float speed={2} rotationIntensity={0} floatIntensity={0.5}>
                <mesh position={[0, 1.7, 0]}>
                    <sphereGeometry args={[0.08, 8, 8]} />
                    <meshStandardMaterial
                        color={moodColors[mood] || moodColors.neutral}
                        emissive={moodColors[mood] || moodColors.neutral}
                        emissiveIntensity={0.5}
                    />
                </mesh>
            </Float>

            {/* Active highlight */}
            {isActive && (
                <pointLight
                    position={[0, 2, 0]}
                    color="#d4af37"
                    intensity={2}
                    distance={3}
                />
            )}
        </group>
    );
}

// Player indicator
interface PlayerProps {
    position: [number, number, number];
}

function Player({ position }: PlayerProps) {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((state) => {
        if (meshRef.current) {
            meshRef.current.rotation.y = state.clock.elapsedTime;
        }
    });

    return (
        <group position={position}>
            {/* Player marker */}
            <mesh ref={meshRef} position={[0, 0.5, 0]} castShadow>
                <cylinderGeometry args={[0.3, 0.3, 0.1, 16]} />
                <meshStandardMaterial color="#d4af37" emissive="#d4af37" emissiveIntensity={0.3} />
            </mesh>

            {/* Direction arrow */}
            <mesh position={[0, 0.6, 0.4]} rotation={[Math.PI / 2, 0, 0]}>
                <coneGeometry args={[0.1, 0.3, 8]} />
                <meshStandardMaterial color="#d4af37" />
            </mesh>

            <pointLight position={[0, 1, 0]} color="#d4af37" intensity={1} distance={5} />
        </group>
    );
}

// Medieval decorations
function Decorations() {
    return (
        <>
            {/* Torch posts */}
            {[[-8, 0, 8], [8, 0, 8], [-8, 0, -8], [8, 0, -8]].map((pos, i) => (
                <group key={i} position={pos as [number, number, number]}>
                    <mesh position={[0, 1.5, 0]} castShadow>
                        <cylinderGeometry args={[0.1, 0.15, 3, 8]} />
                        <meshStandardMaterial color="#4a3728" />
                    </mesh>
                    <pointLight
                        position={[0, 3.2, 0]}
                        color="#ff6b35"
                        intensity={1}
                        distance={10}
                        castShadow
                    />
                    <Sparkles
                        count={10}
                        scale={[0.5, 0.5, 0.5]}
                        position={[0, 3.2, 0]}
                        color="#ff6b35"
                        size={2}
                    />
                </group>
            ))}

            {/* Center fountain */}
            <group position={[0, 0, 0]}>
                <mesh position={[0, 0.3, 0]} receiveShadow>
                    <cylinderGeometry args={[1.5, 2, 0.6, 16]} />
                    <meshStandardMaterial color="#6b6b6b" roughness={0.9} />
                </mesh>
                <mesh position={[0, 0.7, 0]}>
                    <cylinderGeometry args={[0.3, 0.3, 0.8, 8]} />
                    <meshStandardMaterial color="#5a5a5a" roughness={0.8} />
                </mesh>
            </group>
        </>
    );
}

// Scene content
function SceneContent() {
    const worldState = useAppStore((state) => state.worldState);

    const playerPosition: [number, number, number] = worldState?.player?.position
        ? [worldState.player.position[0], worldState.player.position[1], worldState.player.position[2]]
        : [0, 0, 5];

    return (
        <>
            {/* Lighting */}
            <ambientLight intensity={0.3} />
            <directionalLight
                position={[10, 15, 10]}
                intensity={0.8}
                castShadow
                shadow-mapSize={[2048, 2048]}
            />

            {/* Environment */}
            <fog attach="fog" args={['#1a1a2e', 15, 50]} />
            <color attach="background" args={['#1a1a2e']} />

            {/* Ground */}
            <Ground />

            {/* Decorations */}
            <Decorations />

            {/* Market stalls */}
            <Stall position={[5, 0, 0]} color="#b87333" name="Apples" isActive />
            <Stall position={[-5, 0, 3]} color="#c9a86c" name="Bread" />
            <Stall position={[0, 0, -5]} color="#8b4513" name="Meat" />

            {/* NPCs from world state */}
            {worldState?.npcs?.map((npc) => (
                <NPC
                    key={npc.id}
                    position={npc.position}
                    name={npc.name}
                    mood={npc.mood}
                />
            )) || (
                    <>
                        <NPC position={[5, 0, 2]} name="Gregor" mood="friendly" isActive />
                        <NPC position={[-5, 0, 5]} name="Martha" mood="neutral" />
                        <NPC position={[0, 0, -3]} name="Boris" mood="neutral" />
                    </>
                )}

            {/* Player */}
            <Player position={playerPosition} />

            {/* Controls */}
            <OrbitControls
                enablePan={true}
                enableZoom={true}
                minDistance={5}
                maxDistance={30}
                target={[0, 0, 0]}
            />
        </>
    );
}

// Main World component
export function World() {
    return (
        <div className="canvas-container">
            <Canvas
                shadows
                camera={{ position: [8, 8, 12], fov: 60 }}
                gl={{ antialias: true }}
            >
                <SceneContent />
            </Canvas>
        </div>
    );
}
