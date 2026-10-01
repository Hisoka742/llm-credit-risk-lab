import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

/*
  The hero field is data, not decoration: one mote per loan in the study, and the share of
  warm motes equals the real default rate. Positions are seeded, so the field is identical
  on every load (the study seeds everything too).

  All motion runs in the vertex shader. The CPU only updates three uniforms per frame.
*/

const VERTEX = /* glsl */ `
  uniform float uTime;
  uniform float uScroll;
  uniform float uPixelRatio;
  attribute float aPhase;
  attribute float aSize;
  attribute vec3 aColor;
  attribute float aAlpha;
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vec3 p = position;
    p.y += sin(uTime * 0.11 + aPhase) * 0.16 + uScroll * (0.5 + aSize * 0.25);
    p.x += cos(uTime * 0.08 + aPhase * 1.7) * 0.12;
    // Wrap vertically so the field never runs out while the page scrolls.
    p.y = mod(p.y + 7.0, 14.0) - 7.0;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = aSize * uPixelRatio * (11.0 / -mv.z);
    vColor = aColor;
    vAlpha = aAlpha * smoothstep(-15.0, -4.0, mv.z);
  }
`;

const FRAGMENT = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.12, d) * vAlpha;
    if (a < 0.01) discard;
    gl_FragColor = vec4(vColor, a);
  }
`;

function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type FieldProps = { count: number; defaultRate: number; animate: boolean };

function Motes({ count, defaultRate, animate }: FieldProps) {
  const group = useRef<THREE.Group>(null);
  const material = useRef<THREE.ShaderMaterial>(null);
  const pointer = useRef({ x: 0, y: 0 });
  const { gl, invalidate } = useThree();

  const geometry = useMemo(() => {
    const rand = mulberry32(42);
    const position = new Float32Array(count * 3);
    const color = new Float32Array(count * 3);
    const phase = new Float32Array(count);
    const size = new Float32Array(count);
    const alpha = new Float32Array(count);
    const warm = new THREE.Color("#ff5a3c");
    const paper = new THREE.Color("#f1ece2");
    for (let i = 0; i < count; i++) {
      position[i * 3] = (rand() - 0.5) * 26;
      position[i * 3 + 1] = (rand() - 0.5) * 14;
      position[i * 3 + 2] = -rand() * 11 + 2;
      const defaulted = rand() < defaultRate;
      const c = defaulted ? warm : paper;
      color[i * 3] = c.r;
      color[i * 3 + 1] = c.g;
      color[i * 3 + 2] = c.b;
      phase[i] = rand() * Math.PI * 2;
      size[i] = defaulted ? 1.7 + rand() * 1.0 : 1.0 + rand() * 1.0;
      alpha[i] = defaulted ? 0.9 : 0.32 + rand() * 0.24;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(position, 3));
    g.setAttribute("aColor", new THREE.BufferAttribute(color, 3));
    g.setAttribute("aPhase", new THREE.BufferAttribute(phase, 1));
    g.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
    g.setAttribute("aAlpha", new THREE.BufferAttribute(alpha, 1));
    return g;
  }, [count, defaultRate]);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uScroll: { value: 0 },
      uPixelRatio: { value: 1 },
    }),
    [],
  );

  useEffect(() => () => geometry.dispose(), [geometry]);

  useEffect(() => {
    if (!animate) return;
    const onMove = (e: PointerEvent) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [animate]);

  useEffect(() => {
    // Static render for reduced motion: one frame, then stop.
    if (!animate) invalidate();
  }, [animate, invalidate]);

  useFrame((state, delta) => {
    const m = material.current;
    if (!m) return;
    m.uniforms.uPixelRatio.value = gl.getPixelRatio();
    if (!animate) return;
    m.uniforms.uTime.value = state.clock.elapsedTime;
    m.uniforms.uScroll.value = window.scrollY / Math.max(1, window.innerHeight);
    const g = group.current;
    if (g) {
      // Ease toward the pointer: the field leans a few degrees, with weight.
      const k = 1 - Math.exp(-delta * 2.2);
      g.rotation.y += (pointer.current.x * 0.09 - g.rotation.y) * k;
      g.rotation.x += (pointer.current.y * 0.06 - g.rotation.x) * k;
    }
  });

  return (
    <group ref={group}>
      <points geometry={geometry} frustumCulled={false}>
        <shaderMaterial
          ref={material}
          vertexShader={VERTEX}
          fragmentShader={FRAGMENT}
          uniforms={uniforms}
          transparent
          depthWrite={false}
        />
      </points>
    </group>
  );
}

export default function LoanField(props: FieldProps) {
  return (
    <Canvas
      camera={{ position: [0, 0, 6], fov: 55, near: 0.1, far: 40 }}
      dpr={[1, 1.75]}
      frameloop={props.animate ? "always" : "demand"}
      gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
      aria-hidden="true"
    >
      <Motes {...props} />
    </Canvas>
  );
}
