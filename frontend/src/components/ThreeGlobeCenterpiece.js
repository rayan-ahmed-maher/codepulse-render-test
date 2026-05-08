"use client";

import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { Sphere, Torus, PointLight } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';

const GlobeMesh = () => {
  const globeRef = useRef();
  
  // Load the earth texture
  const texture = useLoader(THREE.TextureLoader, 'https://raw.githubusercontent.com/vasturiano/three-globe/master/example/img/earth-dark.jpg');

  useFrame((state, delta) => {
    // Globe auto-rotates at 0.003 rad/frame (approx 0.18 rad/sec at 60fps)
    if (globeRef.current) {
      globeRef.current.rotation.y += 0.003;
    }
  });

  return (
    <group ref={globeRef}>
      <Sphere args={[1.82, 64, 64]}>
        <meshStandardMaterial 
          color="#0A1628"
          roughness={0.7}
          metalness={0.1}
          emissive="#00D4FF"
          emissiveMap={texture}
          emissiveIntensity={1.2}
          wireframe={false}
        />
      </Sphere>
      
      {/* Faint blue latitude/longitude grid wireframe */}
      <Sphere args={[1.83, 32, 32]}>
        <meshBasicMaterial 
          color="#1A3A5C"
          wireframe={true}
          transparent={true}
          opacity={0.15}
        />
      </Sphere>
    </group>
  );
};

const OrbitalRing = ({ color, tiltX, speedSec, clockwise, nodeCount }) => {
  const ringGroupRef = useRef();
  const nodesRef = useRef([]);

  useFrame((state, delta) => {
    if (ringGroupRef.current) {
      const direction = clockwise ? -1 : 1;
      const speed = (Math.PI * 2) / speedSec;
      // Z-axis rotation to spin the ring along its own path
      ringGroupRef.current.rotation.z += speed * delta * direction;
    }

    // Node opacity pulse
    const time = state.clock.getElapsedTime();
    const pulse = 0.7 + (Math.sin(time * Math.PI) + 1) * 0.15; // Maps to 0.7 - 1.0 (2 second cycle = time * Math.PI)
    nodesRef.current.forEach(node => {
      if (node && node.material) {
        node.material.opacity = pulse;
      }
    });
  });

  // Calculate node positions evenly spaced along the torus
  const nodePositions = useMemo(() => {
    const positions = [];
    const radius = 2.34; // Matches torus radius
    for (let i = 0; i < nodeCount; i++) {
      const angle = (i / nodeCount) * Math.PI * 2;
      positions.push([
        Math.cos(angle) * radius,
        Math.sin(angle) * radius,
        0
      ]);
    }
    return positions;
  }, [nodeCount]);

  return (
    <group rotation={[tiltX * (Math.PI / 180), 0, 0]}>
      <group ref={ringGroupRef}>
        <Torus args={[2.34, 0.015, 16, 100]}>
          <meshBasicMaterial color={color} transparent opacity={0.6} />
        </Torus>
        
        {nodePositions.map((pos, i) => (
          <group key={i} position={pos}>
            <Sphere args={[0.04, 16, 16]} ref={el => nodesRef.current[i] = el}>
              <meshStandardMaterial 
                color={color} 
                emissive={color}
                emissiveIntensity={2}
                transparent
                opacity={1}
              />
            </Sphere>
            <pointLight color={color} intensity={0.5} distance={1.5} />
          </group>
        ))}
      </group>
    </group>
  );
};

export default function ThreeGlobeCenterpiece() {
  return (
    <div style={{ width: '100%', height: '100%', position: 'absolute', inset: 0, zIndex: 1 }}>
      <Canvas camera={{ position: [0, 0, 8], fov: 45 }}>
        {/* Environment Lighting */}
        <ambientLight color="#1A1A4A" intensity={0.3} />
        <pointLight color="#00D4FF" intensity={2.0} position={[10, 10, 5]} />
        <pointLight color="#FF00FF" intensity={1.5} position={[-10, -10, 5]} />

        <GlobeMesh />

        {/* 
          Ring 1 (cyan #00D4FF): 20s rotation, tilted 15deg on X
          Ring 2 (magenta #FF2D9B): 25s rotation, tilted 75deg on X, counter-clockwise
          Ring 3 (cyan #00BFFF): 35s rotation, tilted 45deg on X
        */}
        <OrbitalRing color="#00D4FF" tiltX={15} speedSec={20} clockwise={true} nodeCount={6} />
        <OrbitalRing color="#FF2D9B" tiltX={75} speedSec={25} clockwise={false} nodeCount={6} />
        <OrbitalRing color="#00BFFF" tiltX={45} speedSec={35} clockwise={true} nodeCount={6} />

        <EffectComposer>
          <Bloom 
            intensity={1.5} 
            luminanceThreshold={0.2} 
            luminanceSmoothing={0.9} 
            radius={0.8} 
          />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
