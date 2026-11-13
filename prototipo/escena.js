// Mío vs Nuestro · prototipo de gráficos «nivel 2» (semirrealista).
// Escena de prueba: valle con río, dos poblados prehistóricos iguales en riqueza (marcas verde y naranja),
// personas MakeHuman (CC0) con animaciones UAL (CC0), terreno y agua con texturas, cielo físico y sombras.
// Modo web: cámara libre, medidor de FPS y calidad automática (alta / media / baja).
// Modo reel (?reel=1&plano=general|poblado|cerca&dur=8): tiempo fotograma a fotograma con window.paso(dt),
// igual que reels/fabrica.py, para medir cuánto tarda el servidor en grabar.
import * as THREE from 'three';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { MeshoptDecoder } from './vendor/meshopt_decoder.module.js';
import { Sky } from './vendor/Sky.js';
import { Water } from './vendor/Water.js';
import * as SkeletonUtils from './vendor/SkeletonUtils.js';
import { OrbitControls } from './vendor/OrbitControls.js';
import { mergeVertices } from './vendor/BufferGeometryUtils.js';

const P = new URLSearchParams(location.search);
const REEL = P.get('reel') === '1';
const PLANO = P.get('plano') || 'general';
const LADO = P.get('lado') === 'B' ? 'B' : 'A';
const MOVIL = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) || (navigator.maxTouchPoints > 1 && Math.min(screen.width, screen.height) < 820);
const V = THREE.Vector3, Q = THREE.Quaternion, ss = THREE.MathUtils.smoothstep, lerp = THREE.MathUtils.lerp;

// ---------- aleatorio con semilla (la escena sale siempre igual) ----------
function azar(semilla) { let a = semilla >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const R = azar(7);

// ---------- renderer, escena, cámara ----------
const lienzo = document.getElementById('mundo');
const renderer = new THREE.WebGLRenderer({ canvas: lienzo, antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: REEL });
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.5;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const escena = new THREE.Scene();
escena.fog = new THREE.FogExp2(0xaebfc6, 0.0042);
const camara = new THREE.PerspectiveCamera(REEL ? 50 : 55, 1, 0.1, 2000);
camara.position.set(-58, 34, 62);

// ---------- terreno ----------
const rioX = z => 7 * Math.sin(z * 0.028) + 3 * Math.sin(z * 0.071 + 1.3);
const ruido = (x, z) => Math.sin(x * 0.11 + z * 0.07) * 0.6 + Math.sin(x * 0.05 - z * 0.13 + 2) * 0.8 + Math.sin(x * 0.23 + z * 0.19) * 0.25 + Math.sin(x * 0.017 + z * 0.021) * 1.6;
function alturaBase(x, z) {
  const d = Math.abs(x - rioX(z));
  const orilla = ss(d, 3.5, 11);
  let h = -2.2 * (1 - orilla) + orilla * (ruido(x, z) * 0.9 * ss(d, 12, 40) + Math.max(0, d - 30) * 0.07);
  const borde = Math.max(0, Math.hypot(x * 0.9, z) - 80);
  return h + borde * borde * 0.014;
}
const CAMPOS = [{ lado: 'A', x: -21, z: 9, color: 0x1d9e75 }, { lado: 'B', x: 23, z: -7, color: 0xd85a30 }];
for (const c of CAMPOS) c.h = alturaBase(c.x, c.z);
function altura(x, z) {
  let h = alturaBase(x, z);
  for (const c of CAMPOS) { const k = ss(1 - Math.hypot(x - c.x, z - c.z) / 15, 0, 1); h = lerp(h, c.h, k); }
  return h;
}
const NIVEL_AGUA = -0.9;

const cargador = new THREE.TextureLoader();
function tex(ruta, rep, srgb) {
  const t = cargador.load(ruta, () => { pendientes--; progreso(); });
  pendientes++; total++;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep, rep); t.anisotropy = 8;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
let pendientes = 0, total = 0;

function terreno() {
  const TAM = 260, N = 170;
  const g = new THREE.PlaneGeometry(TAM, TAM, N, N); g.rotateX(-Math.PI / 2);
  const pos = g.attributes.position, col = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), z = pos.getZ(i), h = altura(x, z); pos.setY(i, h);
    const d = Math.abs(x - rioX(z));
    let c = new THREE.Color(1, 1, 1).multiplyScalar(0.9 + 0.12 * Math.sin(x * 0.3 + z * 0.2) * Math.sin(z * 0.17));
    c.lerp(new THREE.Color(0.62, 0.52, 0.38), 1 - ss(d, 4, 7.5));                       // orilla de barro
    for (const k of CAMPOS) c.lerp(new THREE.Color(0.66, 0.55, 0.42), 0.85 * (1 - ss(Math.hypot(x - k.x, z - k.z), 4, 11))); // tierra pisada
    c.lerp(new THREE.Color(0.6, 0.6, 0.58), ss(h, 6, 14));                                // roca en las montañas
    col.set([c.r, c.g, c.b], i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3)); g.computeVertexNormals();
  const m = new THREE.MeshStandardMaterial({ map: tex('tex/hierba.jpg', 44, true), normalMap: tex('tex/hierba_n.jpg', 44), normalScale: new THREE.Vector2(0.8, 0.8), vertexColors: true, roughness: 0.95, metalness: 0 });
  m.color.setRGB(0.6, 0.66, 0.5);
  const t = new THREE.Mesh(g, m); t.receiveShadow = true; escena.add(t);
}

// ---------- cielo, sol y agua ----------
const sol = new V();
const cielo = new Sky(); cielo.scale.setScalar(4000);
Object.assign(cielo.material.uniforms, {});
cielo.material.uniforms.turbidity.value = 5; cielo.material.uniforms.rayleigh.value = 1.4;
cielo.material.uniforms.mieCoefficient.value = 0.004; cielo.material.uniforms.mieDirectionalG.value = 0.82;
sol.setFromSphericalCoords(1, THREE.MathUtils.degToRad(90 - 16), THREE.MathUtils.degToRad(215));
cielo.material.uniforms.sunPosition.value.copy(sol);
escena.add(cielo);
const pmrem = new THREE.PMREMGenerator(renderer);
const escCielo = new THREE.Scene(); const cieloCopia = new Sky(); cieloCopia.scale.setScalar(4000);
for (const k of ['turbidity', 'rayleigh', 'mieCoefficient', 'mieDirectionalG']) cieloCopia.material.uniforms[k].value = cielo.material.uniforms[k].value;
cieloCopia.material.uniforms.sunPosition.value.copy(sol); escCielo.add(cieloCopia);
escena.environment = pmrem.fromScene(escCielo).texture;

const luzSol = new THREE.DirectionalLight(0xffe2b8, 2.6);
luzSol.position.copy(sol).multiplyScalar(120); luzSol.castShadow = true;
const sc = luzSol.shadow.camera; sc.left = -48; sc.right = 48; sc.top = 40; sc.bottom = -40; sc.near = 10; sc.far = 300;
luzSol.shadow.bias = -0.0004; luzSol.shadow.normalBias = 0.04;
escena.add(luzSol, luzSol.target);
escena.add(new THREE.HemisphereLight(0xcfe2ff, 0x5a4a32, 0.55));

const normalesAgua = tex('tex/agua_n.jpg', 1);
const geoAgua = new THREE.PlaneGeometry(260, 260);
const aguaReflejo = new Water(geoAgua, { textureWidth: 512, textureHeight: 512, waterNormals: normalesAgua, sunDirection: sol.clone(), sunColor: 0xfff1d6, waterColor: 0x1f4b50, distortionScale: 2.2, fog: true });
aguaReflejo.rotation.x = -Math.PI / 2; aguaReflejo.position.y = NIVEL_AGUA; aguaReflejo.material.uniforms.size.value = 6;
const aguaSimple = new THREE.Mesh(geoAgua, new THREE.MeshStandardMaterial({ color: 0x2c5b62, roughness: 0.12, metalness: 0.2, transparent: true, opacity: 0.92 }));
aguaSimple.rotation.x = -Math.PI / 2; aguaSimple.position.y = NIVEL_AGUA;
escena.add(aguaReflejo, aguaSimple);

// ---------- texturas hechas a mano (cuero, fibra, hierba) ----------
function lienzoTex(tam, dibujar, rep = 1) {
  const c = document.createElement('canvas'); c.width = c.height = tam; dibujar(c.getContext('2d'), tam);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep, rep); t.anisotropy = 4; return t;
}
function cuero(base, semilla) {
  const r = azar(semilla);
  return (x, tam) => {
    x.fillStyle = base; x.fillRect(0, 0, tam, tam);
    for (let i = 0; i < 260; i++) { const a = r(); x.fillStyle = `rgba(${a < 0.5 ? '40,25,12' : '230,200,160'},${0.015 + r() * 0.035})`; x.beginPath(); x.ellipse(r() * tam, r() * tam, 10 + r() * 40, 8 + r() * 26, r() * 3, 0, 7); x.fill(); }
    const d = x.getImageData(0, 0, tam, tam); for (let i = 0; i < d.data.length; i += 4) { const n = (r() - 0.5) * 18; d.data[i] += n; d.data[i + 1] += n; d.data[i + 2] += n; } x.putImageData(d, 0, 0);
    x.strokeStyle = 'rgba(30,18,8,.35)'; x.lineWidth = 1.5; x.setLineDash([5, 4]);
    for (let i = 0; i < 4; i++) { x.beginPath(); const y = r() * tam; x.moveTo(0, y); x.bezierCurveTo(tam * .3, y + 20 * (r() - .5), tam * .7, y + 20 * (r() - .5), tam, y + 10 * (r() - .5)); x.stroke(); }
  };
}
const TEX_CUERO = ['#6b4a2f', '#7d5a3a', '#4f3a28', '#5c4b3a', '#83603c'].map((b, i) => lienzoTex(256, cuero(b, 11 + i), 2));
const TEX_TOLDO = lienzoTex(512, cuero('#8a6a4a', 3), 2);
const TEX_HIERBA = lienzoTex(128, (x, t) => {
  x.clearRect(0, 0, t, t);
  for (let i = 0; i < 26; i++) { const bx = 8 + Math.random() * (t - 16), w = 2 + Math.random() * 3, h = t * (0.45 + Math.random() * 0.55), inc = (Math.random() - 0.5) * 30;
    const g = x.createLinearGradient(0, t, 0, t - h); g.addColorStop(0, '#3e5a22'); g.addColorStop(1, '#a6b85a'); x.fillStyle = g;
    x.beginPath(); x.moveTo(bx - w, t); x.quadraticCurveTo(bx + inc * .3, t - h * .6, bx + inc, t - h); x.quadraticCurveTo(bx + inc * .3 + w * .3, t - h * .6, bx + w, t); x.fill(); }
});
TEX_HIERBA.wrapS = TEX_HIERBA.wrapT = THREE.ClampToEdgeWrapping;

// ---------- vegetación y rocas (instanciadas: miles de piezas en pocas llamadas) ----------
const MAT = (o) => new THREE.MeshStandardMaterial({ roughness: 0.9, metalness: 0, ...o });
function deformar(g0, k, semilla) {
  const g = mergeVertices(g0.deleteAttribute('normal'), 1e-4);
  const r = azar(semilla), p = g.attributes.position, mapa = new Map();
  for (let i = 0; i < p.count; i++) {
    const key = `${p.getX(i).toFixed(3)},${p.getY(i).toFixed(3)},${p.getZ(i).toFixed(3)}`;
    if (!mapa.has(key)) mapa.set(key, 1 + (r() - 0.5) * k);
    const f = mapa.get(key); p.setXYZ(i, p.getX(i) * f, p.getY(i) * (1 + (f - 1) * .5), p.getZ(i) * f);
  }
  g.computeVertexNormals(); return g;
}
function unir(geos) {  // une geometrías no indexadas con su color por vértice
  const gs = geos.map(([g, c, grad = 0]) => { const n = g.index ? g.toNonIndexed() : g; const col = new Float32Array(n.attributes.position.count * 3); const cc = new THREE.Color(c);
    n.computeBoundingBox(); const y0 = n.boundingBox.min.y, y1 = n.boundingBox.max.y, pp = n.attributes.position;
    for (let i = 0; i < col.length; i += 3) { const t = (pp.getY(i / 3) - y0) / Math.max(0.001, y1 - y0), k = 1 - grad + grad * t; col.set([cc.r * k, cc.g * k, cc.b * k], i); } n.setAttribute('color', new THREE.BufferAttribute(col, 3)); n.deleteAttribute('uv'); return n; });
  let total = 0; gs.forEach(g => total += g.attributes.position.count);
  const pos = new Float32Array(total * 3), nor = new Float32Array(total * 3), col = new Float32Array(total * 3); let o = 0;
  for (const g of gs) { pos.set(g.attributes.position.array, o * 3); nor.set(g.attributes.normal.array, o * 3); col.set(g.attributes.color.array, o * 3); o += g.attributes.position.count; }
  const r = new THREE.BufferGeometry(); r.setAttribute('position', new THREE.BufferAttribute(pos, 3)); r.setAttribute('normal', new THREE.BufferAttribute(nor, 3)); r.setAttribute('color', new THREE.BufferAttribute(col, 3)); return r;
}
const INST = [];  // instanciados cuyo número depende de la calidad: {malla, max, fraccion}
function instanciar(geo, mat, puntos, sombra = true) {
  const m = new THREE.InstancedMesh(geo, mat, puntos.length); m.castShadow = sombra; m.receiveShadow = true;
  const d = new THREE.Object3D(), c = new THREE.Color();
  puntos.forEach((p, i) => { d.position.set(p.x, p.y, p.z); d.rotation.set(p.rx || 0, p.ry || 0, p.rz || 0); d.scale.setScalar(p.s); d.updateMatrix(); m.setMatrixAt(i, d.matrix); if (p.c) { c.set(p.c); m.setColorAt(i, c); } });
  escena.add(m); return m;
}
const lejosDeTodo = (x, z, rio = 9, campo = 19) => Math.abs(x - rioX(z)) > rio && CAMPOS.every(c => Math.hypot(x - c.x, z - c.z) > campo) && Math.hypot(x * 0.9, z) < 100;
function bosque() {
  const piso = (r, h, y, sem) => { const g = deformar(new THREE.ConeGeometry(r, h, 16, 4).translate(0, y, 0), 0.22, sem); const p = g.attributes.position;  // ramas que cuelgan en el borde
    for (let i = 0; i < p.count; i++) { const rr = Math.hypot(p.getX(i), p.getZ(i)); p.setY(i, p.getY(i) - Math.pow(rr / r, 3) * 0.35 + Math.sin(Math.atan2(p.getZ(i), p.getX(i)) * 7 + sem) * 0.08 * rr / r); } g.computeVertexNormals(); return g; };
  const pino = unir([[new THREE.CylinderGeometry(0.14, 0.28, 3.2, 8).translate(0, 1.6, 0), 0x4e3828, 0.4],
    [piso(2.1, 2.6, 2.9, 1), 0x2a4426, 0.55], [piso(1.75, 2.4, 3.9, 2), 0x2e4a29, 0.55], [piso(1.4, 2.2, 4.9, 3), 0x33512d, 0.55],
    [piso(1.05, 2.0, 5.8, 4), 0x385732, 0.5], [piso(0.7, 1.7, 6.7, 5), 0x3d5e36, 0.45], [deformar(new THREE.ConeGeometry(0.35, 1.3, 10, 2).translate(0, 7.5, 0), 0.15, 6), 0x42653a, 0.3]]);
  const copa = (r, x, y, z, sem) => deformar(new THREE.IcosahedronGeometry(r, 3).translate(x, y, z), 0.28, sem);
  const roble = unir([[new THREE.CylinderGeometry(0.2, 0.36, 3.2, 8).translate(0, 1.6, 0), 0x56412f, 0.4],
    [copa(1.9, 0, 4.3, 0, 5), 0x45642a, 0.6], [copa(1.5, 1.3, 3.8, 0.4, 6), 0x4e6d33, 0.6],
    [copa(1.45, -1.2, 4.0, -0.5, 7), 0x425f28, 0.6], [copa(1.25, 0.2, 5.4, -0.3, 8), 0x557638, 0.5], [copa(1.1, -0.4, 3.6, 1.2, 9), 0x4a692f, 0.6]]);
  const pinos = [], robles = [], rocas = [], matas = [];
  for (let i = 0; i < 6000 && (pinos.length < 520 || robles.length < 260); i++) {
    const x = (R() - 0.5) * 210, z = (R() - 0.5) * 210;
    if (!lejosDeTodo(x, z)) continue;
    const y = altura(x, z), tono = new THREE.Color().setHSL(0.27 + R() * 0.06, 0.25 + R() * 0.2, 0.8 + R() * 0.3);
    const p = { x, y: y - 0.1, z, ry: R() * 6.3, s: 0.8 + R() * 0.7, c: tono };
    if ((y > 2 || R() < 0.55) && pinos.length < 520) pinos.push(p); else if (robles.length < 260) robles.push(p);
  }
  for (let i = 0; rocas.length < 160 && i < 4000; i++) {
    const z = (R() - 0.5) * 200, cerca = R() < 0.5, x = cerca ? rioX(z) + (R() < 0.5 ? -1 : 1) * (4 + R() * 4) : (R() - 0.5) * 200;
    if (!cerca && !lejosDeTodo(x, z, 4, 10)) continue;
    rocas.push({ x, y: altura(x, z) - 0.15, z, rx: R(), ry: R() * 6, rz: R(), s: 0.25 + R() * (cerca ? 0.6 : 1.4), c: new THREE.Color().setHSL(0.08, 0.05, 0.22 + R() * 0.14) });
  }
  for (let i = 0; matas.length < 3200 && i < 30000; i++) {
    const c = CAMPOS[i % 2], cerca = R() < 0.55, a = R() * 6.3, rr = 5 + R() * 22;
    const x = cerca ? c.x + Math.cos(a) * rr : (R() - 0.5) * 160, z = cerca ? c.z + Math.sin(a) * rr : (R() - 0.5) * 160;
    if (Math.abs(x - rioX(z)) < 5.5 || CAMPOS.some(k => Math.hypot(x - k.x, z - k.z) < 6.5)) continue;
    matas.push({ x, y: altura(x, z), z, ry: R() * 6.3, s: 0.6 + R() * 0.7, c: new THREE.Color().setHSL(0.2 + R() * 0.06, 0.3, 0.55 + R() * 0.25) });
  }
  const matArbol = MAT({ vertexColors: true, roughness: 0.85 });
  INST.push({ m: instanciar(pino, matArbol, pinos), f: { alta: 1, media: 0.7, baja: 0.45 } });
  INST.push({ m: instanciar(roble, matArbol, robles), f: { alta: 1, media: 0.7, baja: 0.45 } });
  INST.push({ m: instanciar(deformar(new THREE.IcosahedronGeometry(1, 2), 0.45, 9).scale(1, 0.62, 1), MAT({ color: 0xffffff, roughness: 1 }), rocas), f: { alta: 1, media: 1, baja: 0.6 } });
  const mata = new THREE.PlaneGeometry(0.8, 0.45).translate(0, 0.225, 0); const m2 = mata.clone().rotateY(Math.PI / 2); const m3 = mata.clone().rotateY(Math.PI / 4);
  const matHierba = MAT({ map: TEX_HIERBA, alphaTest: 0.45, side: THREE.DoubleSide, roughness: 1 });
  matHierba.onBeforeCompile = s => { s.uniforms.uTiempo = uTiempo; s.vertexShader = 'uniform float uTiempo;\n' + s.vertexShader.replace('#include <begin_vertex>',
    '#include <begin_vertex>\n vec4 _b = instanceMatrix * vec4(0.,0.,0.,1.); transformed.x += sin(uTiempo*1.7 + _b.x*0.3 + _b.z*0.2) * 0.12 * uv.y;'); };
  INST.push({ m: instanciar(unirSimple([mata, m2, m3]), matHierba, matas, false), f: { alta: 1, media: 0.4, baja: 0 } });
}
function unirSimple(gs) { const n = gs.map(g => g.toNonIndexed()); let t = 0; n.forEach(g => t += g.attributes.position.count);
  const out = new THREE.BufferGeometry(); for (const k of ['position', 'normal', 'uv']) { const it = n[0].attributes[k].itemSize, arr = new Float32Array(t * it); let o = 0; for (const g of n) { arr.set(g.attributes[k].array, o); o += g.attributes[k].array.length; } out.setAttribute(k, new THREE.BufferAttribute(arr, it)); } return out; }
const uTiempo = { value: 0 };

// ---------- poblados: chozas, hoguera, secadero, leña, lanzas, banderín ----------
const FUEGOS = [];
function choza(x, z, giro, s = 1) {
  const g = new THREE.Group(), y = altura(x, z), ap = new V(0, 3.5, 0), matPalo = MAT({ color: 0x6b4e33 });
  for (let i = 0; i < 15; i++) { const a = i / 15 * Math.PI * 2, base = new V(Math.cos(a) * 1.85, 0, Math.sin(a) * 1.85), dir = ap.clone().sub(base), L = dir.length() + 0.55;
    const p = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.06, L, 5), matPalo); p.position.copy(base).addScaledVector(dir.normalize(), L / 2); p.quaternion.setFromUnitVectors(new V(0, 1, 0), dir); p.castShadow = true; g.add(p); }
  const toldo = new THREE.Mesh(new THREE.ConeGeometry(1.98, 3.15, 22, 5, true, 0.5, Math.PI * 2 - 1.0), MAT({ map: TEX_TOLDO, side: THREE.DoubleSide, roughness: 0.95 }));
  toldo.geometry = deformar(toldo.geometry, 0.05, 13); toldo.position.y = 1.58; toldo.castShadow = toldo.receiveShadow = true; g.add(toldo);
  g.position.set(x, y - 0.05, z); g.rotation.y = giro; g.scale.setScalar(s); escena.add(g); return g;
}
function hoguera(x, z) {
  const g = new THREE.Group(), y = altura(x, z);
  for (let i = 0; i < 10; i++) { const a = i / 10 * Math.PI * 2, p = new THREE.Mesh(deformar(new THREE.IcosahedronGeometry(0.2, 1), 0.4, 20 + i).scale(1, 0.7, 1), MAT({ color: 0x77736b }));
    p.position.set(Math.cos(a) * 0.75, 0.08, Math.sin(a) * 0.75); p.castShadow = true; g.add(p); }
  for (let i = 0; i < 5; i++) { const l = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.08, 1.1, 6), MAT({ color: i % 2 ? 0x3a2a1c : 0x4a3524 }));
    l.rotation.z = Math.PI / 2 - 0.45; l.rotation.y = i / 5 * Math.PI * 2; l.position.y = 0.25; g.add(l); }
  const brasa = new THREE.Mesh(new THREE.CircleGeometry(0.45, 16), new THREE.MeshBasicMaterial({ color: 0xff6a20 })); brasa.rotation.x = -Math.PI / 2; brasa.position.y = 0.03; g.add(brasa);
  const llamas = [];
  for (let i = 0; i < 4; i++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: TEX_LLAMA, color: 0xffb060, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true })); sp.position.y = 0.5; g.add(sp); llamas.push(sp); }
  const humo = [];
  for (let i = 0; i < 10; i++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: TEX_HUMO, color: 0x9a9690, depthWrite: false, transparent: true, opacity: 0 })); g.add(sp); humo.push(sp); }
  const luz = new THREE.PointLight(0xff8a3d, 25, 14, 2); luz.position.y = 1; g.add(luz);
  g.position.set(x, y, z); escena.add(g); FUEGOS.push({ llamas, humo, luz, f: R() * 10 });
}
const TEX_LLAMA = lienzoTex(64, (x, t) => { const g = x.createRadialGradient(t / 2, t * .6, 1, t / 2, t * .55, t / 2); g.addColorStop(0, 'rgba(255,240,200,1)'); g.addColorStop(.35, 'rgba(255,150,40,.85)'); g.addColorStop(1, 'rgba(255,60,0,0)'); x.fillStyle = g; x.fillRect(0, 0, t, t); });
const TEX_HUMO = lienzoTex(64, (x, t) => { const g = x.createRadialGradient(t / 2, t / 2, 1, t / 2, t / 2, t / 2); g.addColorStop(0, 'rgba(255,255,255,.55)'); g.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = g; x.fillRect(0, 0, t, t); });
function secadero(x, z, giro) {
  const g = new THREE.Group(), m = MAT({ color: 0x6b4e33 });
  for (const sx of [-1, 1]) for (const sz of [-0.35, 0.35]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.05, 2.1, 5), m); p.position.set(sx * 1.1, 1, sz * 0.6); p.rotation.x = sz * 0.6; p.castShadow = true; g.add(p); }
  const barra = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 2.6, 5), m); barra.rotation.z = Math.PI / 2; barra.position.y = 1.9; g.add(barra);
  const piel = new THREE.Mesh(deformar(new THREE.PlaneGeometry(1.5, 1.2, 6, 6), 0.15, 30), MAT({ map: TEX_CUERO[3], side: THREE.DoubleSide })); piel.position.set(0, 1.3, 0.02); piel.castShadow = true; g.add(piel);
  g.position.set(x, altura(x, z), z); g.rotation.y = giro; escena.add(g);
}
function lenya(x, z, giro) {
  const g = new THREE.Group();
  for (let f = 0; f < 3; f++) for (let i = 0; i < 4 - f; i++) { const l = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.12, 1.4, 7), MAT({ color: [0x5a4330, 0x6b5039, 0x4e3a29][(i + f) % 3] }));
    l.rotation.z = Math.PI / 2; l.position.set(0, 0.11 + f * 0.2, (i - (3 - f) / 2) * 0.23); l.castShadow = true; g.add(l); }
  g.position.set(x, altura(x, z), z); g.rotation.y = giro; escena.add(g);
}
function lanza() { const g = new THREE.Group(); const p = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.03, 2.3, 5), MAT({ color: 0x7a5a3c })); p.position.y = 1.15; g.add(p);
  const pu = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.24, 5), MAT({ color: 0x55524c, roughness: 0.6 })); pu.position.y = 2.4; g.add(pu);
  const atado = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.12, 6), MAT({ color: 0xa08a60 })); atado.position.y = 2.25; g.add(atado); g.traverse(o => o.castShadow = true); return g; }
function banderin(x, z, color) {
  const g = new THREE.Group(), m = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.05, 3.2, 5), MAT({ color: 0x6b4e33 })); m.position.y = 1.6; g.add(m);
  const tela = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.55, 8, 2), MAT({ color, side: THREE.DoubleSide, roughness: 0.8 })); tela.position.set(0.47, 2.8, 0); g.add(tela);
  g.position.set(x, altura(x, z), z); escena.add(g); BANDERAS.push(tela);
}
const BANDERAS = [];
function poblado(c) {
  const { x, z } = c;
  choza(x - 5.5, z - 3, 0.4); choza(x + 4.5, z - 4.5, -0.6, 0.92); choza(x + 1, z + 6, 3.1, 1.05);
  hoguera(x, z);
  secadero(x - 6, z + 4, 0.9); lenya(x + 3.2, z + 2.8, 0.3);
  for (let i = 0; i < 3; i++) { const l = lanza(); l.position.set(x - 3.9 + i * 0.25, altura(x - 3.9, z - 1.9), z - 1.9 + i * 0.1); l.rotation.z = -0.32; l.rotation.y = 0.4; escena.add(l); }
  banderin(x + 6.5, z + 1.5, c.color);
  // troncos para sentarse alrededor del fuego
  for (const a of [0.6, 2.4, 4.3]) { const t = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.22, 1.5, 8), MAT({ color: 0x5a4330 })); t.rotation.z = Math.PI / 2; t.rotation.y = -a;
    t.position.set(x + Math.cos(a) * 2.3, altura(x, z) + 0.2, z + Math.sin(a) * 2.3); t.castShadow = t.receiveShadow = true; escena.add(t); }
}

// ---------- personas ----------
const cargadorGLB = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
// Los modelos se piden como .glb; si el alojamiento no sirve .glb (la página publicada en claude.ai), se usan copias en base64 (.b64.txt).
async function bytesDe(ruta) {
  const r = await fetch(ruta); if (r.ok) return r.arrayBuffer();
  const t = await (await fetch(ruta.replace(/\.glb$/, '.b64.txt'))).text(), b = atob(t.trim()), u = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u.buffer;
}
const glb = ruta => { pendientes++; total++; return bytesDe(ruta).then(buf => new Promise((ok, mal) => cargadorGLB.parse(buf, '', g => { pendientes--; progreso(); ok(g); }, mal))); };
const PERSONAS = [], ANIMALES = [];
const PIELES = [0xc89f80, 0x8a5c43, 0xb07f62, 0x6f4a36, 0xd5ad8e];
const SUPERIOR = /^(spine_0[123]|neck_01|Head|clavicle_[lr]|upperarm_[lr]|lowerarm_[lr]|hand_[lr]|(thumb|index|middle|ring|pinky)_0[123]_[lr])\.quaternion$/;
function poseQuieto(andar, t0) {  // la parte de arriba de un fotograma de «andar», con las piernas en reposo: de pie
  const pose = new Map();
  for (const tr of andar.tracks) { if (!SUPERIOR.test(tr.name)) continue; const v = tr.createInterpolant().evaluate(t0); pose.set(tr.name.split('.')[0], new Q(v[0], v[1], v[2], v[3])); }
  return pose;
}
const _pq = new Q(), _r = new Q(), _q = new Q();
function rotarMundo(hueso, eje, ang) { hueso.parent.getWorldQuaternion(_pq); _r.setFromAxisAngle(eje, ang); _q.copy(_pq).invert().multiply(_r).multiply(_pq); hueso.quaternion.premultiply(_q); }
function persona(base, clips, opciones) {
  const m = SkeletonUtils.clone(base.scene);
  const huesos = {}; m.traverse(o => { if (o.isBone) huesos[o.name] = o; if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false;
    if (o.material.name === 'eyes') { o.material = o.material.clone(); o.material.color.set(0x8d8276); o.material.envMapIntensity = 0.3; }
    if (o.material.name === 'body') { o.material = o.material.clone(); o.material.color.set(opciones.piel || PIELES[PERSONAS.length % PIELES.length]).convertSRGBToLinear(); o.material.roughness = 0.72; o.material.envMapIntensity = 0.55; }
    if (/garment_/.test(o.material.name)) { o.material = o.material.clone(); o.material.map = TEX_CUERO[opciones.ropa % TEX_CUERO.length]; o.material.envMapIntensity = 0.6; o.material.color.set(/shoes/.test(o.material.name) ? 0x8a7a6a : 0xffffff); o.material.roughness = 0.92; o.material.metalness = 0; o.material.normalMap = null; } } });
  m.scale.setScalar(opciones.escala || 1);
  const mezcla = new THREE.AnimationMixer(m);
  if (opciones.modo === 'andar') { const accion = mezcla.clipAction(clips.andar); accion.play(); accion.time = (opciones.fase || 0) * clips.andar.duration; }
  escena.add(m);
  // Quien no anda no usa el mezclador: cada fotograma se parte de la postura «de pie» y se le suman los gestos.
  // (El mezclador no vuelve a escribir un clip que no cambia, y los gestos se acumulaban: personajes que se retorcían.)
  const reposo = Object.values(huesos).map(h => [h, (clips.quieto.get(h.name) || h.quaternion).clone()]);
  const p = { m, huesos, mezcla, reposo, ...opciones }; PERSONAS.push(p); return p;
}
const EJE_Y = new V(0, 1, 0);
function animarPersona(p, T, dt) {
  if (p.modo !== 'andar') for (const [h, q] of p.reposo) h.quaternion.copy(q);
  else p.mezcla.update(dt);
  if (p.modo === 'andar') {
    const u = (T * p.vel / p.radio + p.fase * 6.283) % 6.283, c = p.centro;
    const x = c.x + Math.cos(u) * p.radio, z = c.z + Math.sin(u) * p.radio * 0.8;
    p.m.position.set(x, altura(x, z), z);
    const dx = -Math.sin(u) * p.radio, dz = Math.cos(u) * p.radio * 0.8; p.m.rotation.y = Math.atan2(dx, dz);
    return;
  }
  p.m.position.copy(p.pos); p.m.rotation.y = p.giro; p.m.updateMatrixWorld(true);
  const lado = new V(1, 0, 0).applyQuaternion(p.m.quaternion), h = p.huesos;
  const resp = Math.sin(T * 1.6 + p.fase * 5) * 0.025;
  rotarMundo(h.spine_02, lado, resp);
  if (p.modo === 'sentado') {
    p.m.position.y -= 0.42 * (p.escala || 1);
    for (const s of ['l', 'r']) { rotarMundo(h['thigh_' + s], lado, -1.45); h['calf_' + s].parent.updateMatrixWorld(true); rotarMundo(h['calf_' + s], lado, 1.5); }
    for (const s of ['l', 'r']) { h['lowerarm_' + s].parent.updateMatrixWorld(true); rotarMundo(h['lowerarm_' + s], lado, -0.9); }
    rotarMundo(h.spine_01, lado, -0.18);
  } else if (p.modo === 'trabajar') {
    const g = Math.sin(T * 3.2 + p.fase * 3) * 0.18;
    rotarMundo(h.spine_01, lado, -0.25);
    for (const s of ['l', 'r']) { h['upperarm_' + s].parent.updateMatrixWorld(true); rotarMundo(h['upperarm_' + s], lado, -0.55 + g); h['lowerarm_' + s].parent.updateMatrixWorld(true); rotarMundo(h['lowerarm_' + s], lado, -0.9); }
  } else {  // de pie, hablando: gira la cabeza
    h.Head.parent.updateMatrixWorld(true); rotarMundo(h.Head, EJE_Y, Math.sin(T * 0.5 + p.fase * 4) * 0.45);
    h.lowerarm_r.parent.updateMatrixWorld(true); rotarMundo(h.lowerarm_r, lado, -0.5 - 0.35 * Math.max(0, Math.sin(T * 1.3 + p.fase)));
  }
}

// ---------- calidad ----------
const CALIDAD = { alta: { pr: 2, sombra: 2048, reflejo: true }, media: { pr: 1.5, sombra: 1024, reflejo: true }, baja: { pr: 1, sombra: 0, reflejo: false } };
let calidad = REEL ? (CALIDAD[P.get('calidad')] ? P.get('calidad') : 'alta') : (MOVIL ? 'media' : 'alta'), auto = !REEL;
function aplicarCalidad(c) {
  calidad = c; const q = CALIDAD[c];
  renderer.setPixelRatio(REEL ? 1 : Math.min(devicePixelRatio, q.pr));
  const conSombra = q.sombra > 0;
  if (renderer.shadowMap.enabled !== conSombra) { renderer.shadowMap.enabled = conSombra; escena.traverse(o => { if (o.material) [].concat(o.material).forEach(m => m.needsUpdate = true); }); }
  luzSol.castShadow = conSombra;
  if (conSombra && luzSol.shadow.mapSize.x !== q.sombra) { luzSol.shadow.mapSize.set(q.sombra, q.sombra); luzSol.shadow.map?.dispose(); luzSol.shadow.map = null; }
  aguaReflejo.visible = q.reflejo; aguaSimple.visible = !q.reflejo;
  for (const i of INST) i.m.count = Math.floor(i.m.instanceMatrix.count * i.f[c]);
  ajustarTam(); pintarHUD();
}
function ajustarTam() { const w = lienzo.clientWidth || innerWidth, h = lienzo.clientHeight || innerHeight; renderer.setSize(w, h, false); camara.aspect = w / h; camara.updateProjectionMatrix(); }
addEventListener('resize', ajustarTam);

// ---------- cámara: libre en la web, guiada en el reel ----------
const controles = REEL ? null : new OrbitControls(camara, lienzo);
if (controles) { controles.enableDamping = true; controles.maxPolarAngle = 1.45; controles.minDistance = 3; controles.maxDistance = 160; controles.target.set(0, 0, 0); controles.autoRotate = true; controles.autoRotateSpeed = 0.35;
  controles.addEventListener('start', () => controles.autoRotate = false); }
const VISTAS = {
  valle: { pos: [-58, 34, 62], obj: [0, 0, 0] },
  poblado: () => { const c = CAMPOS[0]; return { pos: [c.x - 10, c.h + 6.5, c.z + 10], obj: [c.x, c.h + 1, c.z] }; },
  cerca: () => { const c = CAMPOS[1]; return { pos: [c.x - 4.5, c.h + 1.7, c.z + 4.2], obj: [c.x, c.h + 1.1, c.z] }; },
};
let viaje = null;
function irA(nombre) { const v = typeof VISTAS[nombre] === 'function' ? VISTAS[nombre]() : VISTAS[nombre]; viaje = { t: 0, de: camara.position.clone(), deObj: controles.target.clone(), a: new V(...v.pos), aObj: new V(...v.obj) }; controles.autoRotate = false; }
function camaraReel(T) {
  const dur = parseFloat(P.get('dur') || '8'), u = ss(T / dur, 0, 1), c = CAMPOS[LADO === 'A' ? 0 : 1];
  if (PLANO === 'poblado') { const a = -0.2 + u * 1.1; camara.position.set(c.x + Math.cos(a) * 12.5, c.h + 6.5 - u * 2, c.z + Math.sin(a) * 12.5); camara.lookAt(c.x, c.h + 1, c.z); }
  else if (PLANO === 'cerca') { const w = PERSONAS.find(p => p.lado === LADO && p.modo === 'andar') || PERSONAS[0]; const pos = w.m.position, dir = new V(Math.sin(w.m.rotation.y), 0, Math.cos(w.m.rotation.y));
    const lat = new V(dir.z, 0, -dir.x); camara.position.copy(pos).addScaledVector(dir, 2.6).addScaledVector(lat, 1.6); camara.position.y = pos.y + 1.55; camara.lookAt(pos.x, pos.y + 1.3, pos.z); }
  else { camara.position.set(lerp(-62, -14, u), lerp(40, 16, u), lerp(70, 34, u)); camara.lookAt(lerp(0, -6, u), 0, lerp(0, 4, u)); }
}

// ---------- bucle ----------
let T = 0, fpsCuenta = 0, fpsT = 0, fps = 0, bajadas = 0, desdeAjuste = 0;
function actualizar(dt) {
  T += dt; uTiempo.value = T;
  if (aguaReflejo.visible) aguaReflejo.material.uniforms.time.value = T * 0.6;
  for (const f of FUEGOS) {
    f.luz.intensity = 22 + 8 * Math.sin(T * 13 + f.f) * Math.sin(T * 7.3 + f.f * 2);
    f.llamas.forEach((s, i) => { const k = 0.75 + 0.25 * Math.sin(T * (9 + i * 2.1) + i + f.f); s.scale.set(0.7 * k, 1.25 * k, 1); s.position.set(Math.sin(T * 5 + i * 2) * 0.08, 0.45 + i * 0.07, Math.cos(T * 4 + i) * 0.08); });
    f.humo.forEach((s, i) => { const v = ((T * 0.25 + i / f.humo.length) % 1); s.position.set(Math.sin(v * 6 + i) * 0.3 + v * 0.8, 1.0 + v * 5, Math.cos(v * 5 + i) * 0.3); s.scale.setScalar(0.6 + v * 2.6); s.material.opacity = 0.35 * Math.sin(v * Math.PI); });
  }
  for (const b of BANDERAS) { const p = b.geometry.attributes.position; if (!b.userData.x0) b.userData.x0 = Float32Array.from(p.array);
    for (let i = 0; i < p.count; i++) { const x0 = b.userData.x0[i * 3]; p.setZ(i, Math.sin(T * 4 + x0 * 5) * 0.12 * (x0 + 0.45)); } p.needsUpdate = true; }
  for (const p of PERSONAS) animarPersona(p, T, dt);
  for (const a of ANIMALES) { a.mezcla.update(dt); const u = T * a.vel + a.fase, x = a.c.x + Math.cos(u) * a.r, z = a.c.z + Math.sin(u) * a.r; a.m.position.set(x, altura(x, z), z); a.m.rotation.y = Math.atan2(-Math.sin(u), Math.cos(u)); }
}
function dibujar() { renderer.render(escena, camara); }
let ultimo = performance.now();
function bucle(ahora) {
  const dtReal = (ahora - ultimo) / 1000, dt = Math.min(0.05, dtReal); ultimo = ahora;
  actualizar(dt);
  if (viaje) { viaje.t = Math.min(1, viaje.t + Math.min(0.5, dtReal) / 2.2); const k = ss(viaje.t, 0, 1); camara.position.lerpVectors(viaje.de, viaje.a, k); controles.target.lerpVectors(viaje.deObj, viaje.aObj, k); if (viaje.t >= 1) viaje = null; }
  controles.update();
  dibujar();
  fpsCuenta++; fpsT += dt; desdeAjuste += dt;
  if (fpsT >= 1) { fps = Math.round(fpsCuenta / fpsT); fpsCuenta = 0; fpsT = 0; pintarHUD();
    if (auto && desdeAjuste > 5 && fps < 28 && calidad !== 'baja') { aplicarCalidad(calidad === 'alta' ? 'media' : 'baja'); desdeAjuste = 0; bajadas++; } }
  requestAnimationFrame(bucle);
}

// ---------- HUD ----------
const $ = s => document.querySelector(s);
function pintarHUD() {
  if (REEL) return;
  $('#fps').textContent = fps ? fps + ' fps' : '…';
  document.querySelectorAll('[data-cal]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.cal === (auto ? 'auto' : calidad))));
  $('#cal-actual').textContent = (auto ? 'Auto → ' : '') + calidad;
}
function progreso() { const el = $('#carga-barra'); if (el && total) el.style.width = Math.round(100 * (1 - pendientes / total)) + '%'; }
if (!REEL) {
  document.querySelectorAll('[data-cal]').forEach(b => b.addEventListener('click', () => { const c = b.dataset.cal; auto = c === 'auto'; desdeAjuste = 0; aplicarCalidad(auto ? (MOVIL ? 'media' : 'alta') : c); }));
  document.querySelectorAll('[data-vista]').forEach(b => b.addEventListener('click', () => irA(b.dataset.vista)));
} else { document.body.classList.add('reel'); }

// ---------- montaje ----------
async function montar() {
  terreno(); bosque(); CAMPOS.forEach(poblado);
  const [hombre, mujer, mayor, anim, zorro] = await Promise.all(['modelos/clothed-casual.glb', 'modelos/long-hair.glb', 'modelos/extreme-heavy.glb', 'modelos/clips.glb', 'modelos/zorro.glb'].map(glb));
  const andar = anim.animations.find(a => a.name === 'Walk_Loop');
  const clips = { andar, quieto: poseQuieto(andar, andar.duration * 0.25) };
  // Mismo reparto en los dos poblados: 5 personas, mismas tareas.
  CAMPOS.forEach((c, k) => {
    const y = c.h, o = k ? 2 : 0;
    persona(k ? mujer : hombre, clips, { lado: c.lado, modo: 'andar', centro: new V(c.x, 0, c.z), radio: 8.5, vel: 1.15, fase: 0.1 + k * 0.3, ropa: 0 + o });
    persona(k ? hombre : mujer, clips, { lado: c.lado, modo: 'sentado', pos: new V(c.x + Math.cos(0.6) * 2.3, y, c.z + Math.sin(0.6) * 2.3).addScaledVector(new V(Math.cos(0.6), 0, Math.sin(0.6)), 0.25), giro: Math.atan2(-Math.cos(0.6), -Math.sin(0.6)), fase: 0.2, ropa: 1 + o });
    persona(mayor, clips, { lado: c.lado, modo: 'sentado', pos: new V(c.x + Math.cos(2.4) * 2.55, y, c.z + Math.sin(2.4) * 2.55), giro: Math.atan2(-Math.cos(2.4), -Math.sin(2.4)), fase: 0.5, ropa: 2 + o, escala: 0.97 });
    persona(k ? hombre : mujer, clips, { lado: c.lado, modo: 'trabajar', pos: new V(c.x - 6, altura(c.x - 6, c.z + 2.9), c.z + 2.9), giro: 0, fase: 0.7, ropa: 3 + o });
    persona(k ? mujer : hombre, clips, { lado: c.lado, modo: 'hablar', pos: new V(c.x + 4.6, altura(c.x + 4.6, c.z + 1.4), c.z + 1.4), giro: -1.9, fase: 0.9, ropa: 4 + o, escala: 1.03 });
  });
  // un zorro rondando cada poblado, por el borde del bosque
  const caja = new THREE.Box3().setFromObject(zorro.scene), largo = Math.max(...caja.getSize(new V()).toArray());
  CAMPOS.forEach((c, k) => { const m = SkeletonUtils.clone(zorro.scene); m.scale.setScalar(0.95 / largo); m.traverse(o => { if (o.isMesh) { o.castShadow = true; o.frustumCulled = false; } });
    const mz = new THREE.AnimationMixer(m); mz.clipAction(zorro.animations.find(a => a.name === 'Walk')).play(); escena.add(m);
    ANIMALES.push({ m, mezcla: mz, c: { x: c.x + (k ? 6 : -6), z: c.z + (k ? -10 : 10) }, r: 6, vel: 0.17, fase: k * 2 }); });
  aplicarCalidad(calidad);
  actualizar(0.016);
  if (REEL) { camaraReel(0); dibujar(); window.paso = dt => { actualizar(dt); camaraReel(T); dibujar(); }; window.avanzar = dt => actualizar(dt); requestAnimationFrame(() => { window.listo = true; }); }
  else { $('#carga').hidden = true; requestAnimationFrame(bucle); }
}
ajustarTam();
montar().catch(e => { console.error(e); const el = $('#carga-texto'); if (el) el.textContent = 'No se pudo cargar la escena: ' + e.message; });
