import React, { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, Environment } from '@react-three/drei';
import type { WorldState } from '../hooks/useSimulationSocket';

interface WorldProps {
    gameState: WorldState | null;
}

const Entity = ({ id, data }: { id: string, data: any }) => {
    // Determine color/shape based on ID or data
    const color = id === 'player' ? 'blue' : (data.color || 'red');
    const position: [number, number, number] = [data.x || 0, (data.y || 0) + 0.5, data.z || 0];

    return (
        <mesh position={position}>
            <boxGeometry args={[1, 1, 1]} />
            <meshStandardMaterial color={color} />
        </mesh>
    );
};

export const World: React.FC<WorldProps> = ({ gameState }) => {
    const entities = useMemo(() => {
        if (!gameState || !gameState.entities) return [];
        return Object.entries(gameState.entities).map(([id, data]) => ({ id, data }));
    }, [gameState]);

    return (
        <Canvas camera={{ position: [0, 5, 10], fov: 50 }}>
            <color attach="background" args={['#111']} />
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} />

            <Grid infiniteGrid fadeDistance={30} sectionColor={'#444'} cellColor={'#222'} />

            {entities.map(ent => (
                <Entity key={ent.id} id={ent.id} data={ent.data} />
            ))}

            <OrbitControls />
            <Environment preset="city" />
        </Canvas>
    );
};
