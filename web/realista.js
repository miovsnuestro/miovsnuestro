// Mío vs Nuestro · gráficos «nivel 2» (semirrealistas) sobre el mismo visor y la misma interfaz.
//
// - Personas: cuerpos MakeHuman (CC0) con animación de andar de Quaternius (CC0), en web/modelos/personas/.
//   La figura sencilla de siempre sigue existiendo, invisible: sus posturas (trabajar, sentarse, hablar, las
//   acciones de los reels…) se copian cada fotograma al esqueleto realista, y lo que lleva en la mano se sigue
//   colocando igual. Así no cambia nada de la lógica del visor.
// - Suelo: textura de detalle sobre los colores de siempre.
// - Construcciones: los modelos .glb por época («estructura:casa@prehistoria») los usa obras.js.
//
// ?graficos=1 vuelve a las figuras sencillas. Si los modelos no cargan, se queda con las figuras sencillas.
(function () {
  'use strict';
  const P = new URLSearchParams(location.search);
  const ACTIVO = P.get('graficos') !== '1';
  const R = window.REALISTA = { activo: ACTIVO, listo: false };
  if (!ACTIVO) { window.humanizar = () => {}; window.animarRealista = () => {}; return; }

  const ALTURA = 1.05;                       // altura de un adulto en el visor (la figura sencilla mide lo mismo)
  const PIELES = ['#E2B795', '#CC9C77', '#A8734E', '#8A5A3C', '#D9A985', '#6E4733'];
  const CUEROS = ['#7A5A3C', '#8A6A48', '#6B5034', '#9A7B55', '#5E4A36', '#86704E'];  // cuero curtido y fibra: tonos medios, que se lean como piel de animal y no como tela oscura
  const SUPERIOR = /^(spine_0[123]|neck_01|Head|clavicle_[lr]|upperarm_[lr]|lowerarm_[lr]|hand_[lr]|(thumb|index|middle|ring|pinky)_0[123]_[lr])$/;
  const OCULTAR = /^(eyelashes|brows|tongue|teeth)$/;
  const VACIA = new THREE.BufferGeometry();
  const CINTURON = new THREE.TorusGeometry(0.1, 0.014, 6, 24).rotateX(Math.PI / 2);
  // Textura de cuero curtido (manchas suaves, grano y costuras), común a toda la ropa: el color lo pone cada prenda.
  const TEX_CUERO = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d');
    x.fillStyle = '#d8d8d8'; x.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 220; i++) { x.fillStyle = `rgba(${Math.random() < .5 ? '40,40,40' : '255,255,255'},${.04 + Math.random() * .06})`; x.beginPath(); x.ellipse(Math.random() * 256, Math.random() * 256, 8 + Math.random() * 30, 6 + Math.random() * 18, Math.random() * 3, 0, 7); x.fill(); }
    const d = x.getImageData(0, 0, 256, 256); for (let i = 0; i < d.data.length; i += 4) { const n = (Math.random() - .5) * 26; d.data[i] += n; d.data[i + 1] += n; d.data[i + 2] += n; } x.putImageData(d, 0, 0);
    x.strokeStyle = 'rgba(20,20,20,.45)'; x.setLineDash([5, 4]); x.lineWidth = 1.5; for (const y of [60, 140, 210]) { x.beginPath(); x.moveTo(0, y); x.bezierCurveTo(90, y + 8, 170, y - 8, 256, y + 4); x.stroke(); }
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(2, 2); return t; })();
  const bases = {}, colas = [];
  let andar = null, pose = null;

  function script(src) { return new Promise((ok, mal) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = mal; document.head.appendChild(s); }); }
  function glb(ruta) { return new Promise((ok, mal) => new THREE.GLTFLoader().load(ruta, ok, undefined, mal)); }

  async function preparar() {
    if (!THREE.GLTFLoader) await script('GLTFLoader.js');
    if (!THREE.SkeletonUtils) await script('SkeletonUtils.js');
    if (!THREE.BufferGeometryUtils) await script('BufferGeometryUtils.js');
    const [h, m, v, a] = await Promise.all(['hombre', 'mujer', 'mayor', 'andar'].map(n => glb('modelos/personas/' + n + '.glb')));
    for (const [k, g] of [['hombre', h], ['mujer', m], ['mayor', v]]) {
      const caja = new THREE.Box3().setFromObject(g.scene);
      bases[k] = { escena: g.scene, escala: ALTURA / (caja.max.y - caja.min.y) };
    }
    andar = a.animations.find(c => c.name === 'Walk_Loop');
    // De pie: la parte de arriba de un paso de «andar» (brazos caídos) con las piernas en reposo.
    pose = new Map();
    for (const tr of andar.tracks) { const [n, prop] = tr.name.split('.'); if (prop !== 'quaternion' || !SUPERIOR.test(n)) continue;
      const v4 = tr.createInterpolant().evaluate(andar.duration * 0.25); pose.set(n, new THREE.Quaternion(v4[0], v4[1], v4[2], v4[3])); }
    R.listo = true;
    while (colas.length) humanizar(colas.shift());
  }

  const azar = (id, k) => { let x = Math.sin(id * 12.9898 + k * 78.233) * 43758.5453; return x - Math.floor(x); };
  function ocultarMalla(o) { if (o && o.isMesh && o.geometry !== VACIA) { o.userData.geoOriginal = o.geometry; o.geometry = VACIA; o.castShadow = false; } }

  function humanizar(g) {
    if (!R.listo) { colas.push(g); return; }
    const u = g.userData, a = u.a;
    if (u.real) return;
    const base = bases[(a.edad || 30) >= 55 ? 'mayor' : a.sexo === 'F' ? 'mujer' : 'hombre'];
    const m = THREE.SkeletonUtils.clone(base.escena);
    m.scale.setScalar(base.escala);
    const huesos = {}, piel = PIELES[Math.floor(azar(a.id, 1) * PIELES.length)], cuero = CUEROS[Math.floor(azar(a.id, 2) * CUEROS.length)];
    const ropa = [];
    m.traverse(o => {
      if (o.isBone) huesos[o.name] = o;
      if (!o.isMesh) return;
      if (OCULTAR.test(o.name) || OCULTAR.test(o.material.name)) { o.visible = false; return; }
      o.castShadow = true; o.receiveShadow = true;
      o.material = o.material.clone();
      if (o.material.map) { o.material.map.encoding = THREE.LinearEncoding; o.material.map.needsUpdate = true; }  // el visor no corrige el color de salida: así encaja con el resto
      const n = o.material.name;
      if (n === 'body') { o.material.color.set(piel); o.material.roughness = 0.75; }
      else if (n === 'eyes') o.material.color.set('#8d8276');
      else if (/^garment_/.test(n)) { o.material.map = TEX_CUERO; o.material.normalMap = null; o.material.color.set(/shoes/.test(n) ? '#4a3a2c' : cuero); o.material.roughness = 0.9; o.material.metalness = 0; ropa.push(o.material); }
    });
    // La figura sencilla deja de verse, pero sus grupos siguen ahí: posturas, mano con herramienta, cinturón.
    for (const k of ['torso']) ocultarMalla(u[k]);
    u.cuello.traverse(ocultarMalla);
    for (const b of [u.bI, u.bD, u.pI, u.pD]) b.children.forEach(c => { if (c !== u.herr && c !== u.manoI) ocultarMalla(c); });
    u.cad.children.forEach(c => { if (c.isMesh && c !== u.torso) { c.geometry = CINTURON; c.scale.set(1, 1, 0.72); c.position.y = 0.06; } });  // cinturón fino del color de su gente
    const mezcla = new THREE.AnimationMixer(m), accion = mezcla.clipAction(andar);
    accion.play(); accion.time = azar(a.id, 3) * andar.duration; accion.paused = true;
    const reposo = Object.values(huesos).map(h => [h, (pose.get(h.name) || h.quaternion).clone()]);
    g.add(m);
    u.real = { m, huesos, mezcla, accion, reposo, ropa, cuero, andaba: false, firmaRopa: null, pelvis: huesos.pelvis ? huesos.pelvis.position.clone() : null };
  }

  const _pq = new THREE.Quaternion(), _r = new THREE.Quaternion(), _q = new THREE.Quaternion(), _gq = new THREE.Quaternion();
  const EJE_X = new THREE.Vector3(), EJE_Z = new THREE.Vector3(), ARRIBA = new THREE.Vector3(0, 1, 0);
  function girar(h, eje, ang) { if (!h || !ang) return; h.parent.updateMatrixWorld(true); h.parent.getWorldQuaternion(_pq);
    _r.setFromAxisAngle(eje, ang); _q.copy(_pq).invert().multiply(_r).multiply(_pq); h.quaternion.premultiply(_q); }

  function vestirReal(u) {
    const r = u.real, prendas = (u.a.objetos || []).filter(o => o.categoria === 'ropa');
    const firma = prendas.map(o => o.tipo + (o.color || '') + (o.material || '')).join('|');
    if (r.firmaRopa === firma) return; r.firmaRopa = firma;
    const arriba = prendas.slice().reverse().find(o => ['tunica', 'camisa', 'camiseta', 'abrigo', 'ropa', 'capa'].includes(o.tipo));
    const color = arriba ? (arriba.color || (typeof MATERIAL_ROPA !== 'undefined' && MATERIAL_ROPA[arriba.material]) || r.cuero) : r.cuero;
    r.ropa.forEach(mt => mt.color.set(color));
  }

  function animarRealista(g, andando, dt) {
    const u = g.userData, r = u.real;
    if (!r) return;
    vestirReal(u);
    if (u.extras) u.extras.forEach(x => { if (!x.userData.revisado) { x.userData.revisado = true; let somb = false; x.traverse(o => { const t = o.geometry && o.geometry.type; if (t === 'CylinderGeometry' || t === 'SphereGeometry') somb = true; });  // el sombrero se queda; las cajas de túnica o capa, no
      if (!somb) x.traverse(ocultarMalla); } });
    if (andando) {
      if (!r.andaba) { r.accion.paused = false; r.andaba = true; }
      r.mezcla.update(dt * ((u.a.edad || 30) < 14 ? 1.2 : 1));
      r.m.position.y = 0;
      return;
    }
    if (r.andaba) { r.accion.paused = true; r.andaba = false; }
    for (const [h, q] of r.reposo) h.quaternion.copy(q);
    const H = r.huesos;
    g.getWorldQuaternion(_gq); EJE_X.set(1, 0, 0).applyQuaternion(_gq); EJE_Z.set(0, 0, 1).applyQuaternion(_gq);
    r.m.position.y = (u.cad.position.y - 0.5) * 1.9;  // sentarse o agacharse: la cadera baja como en la figura sencilla
    if (H.pelvis) H.pelvis.position.copy(r.pelvis);
    girar(H.spine_01, EJE_X, u.torso.rotation.x); girar(H.spine_01, EJE_Z, u.torso.rotation.z);
    girar(H.neck_01, EJE_X, u.cuello.rotation.x); girar(H.Head, ARRIBA, u.cuello.rotation.y);
    // La figura sencilla mira hacia +Z como el cuerpo real: su brazo del lado −X es el derecho del cuerpo real.
    girar(H.upperarm_r, EJE_X, u.bI.rotation.x); girar(H.upperarm_r, EJE_Z, u.bI.rotation.z);
    girar(H.upperarm_l, EJE_X, u.bD.rotation.x); girar(H.upperarm_l, EJE_Z, u.bD.rotation.z);
    girar(H.thigh_r, EJE_X, u.pI.rotation.x); girar(H.thigh_l, EJE_X, u.pD.rotation.x);
  }

  window.humanizar = humanizar;
  window.animarRealista = animarRealista;
  preparar().catch(e => { console.warn('Gráficos realistas no disponibles; sigo con las figuras sencillas.', e); R.activo = false; window.humanizar = () => {}; window.animarRealista = () => {}; });

  // ---------- vegetación y rocas: mismas posiciones, formas más naturales y sombreado suave ----------
  // Se cambia solo la forma de cada pieza instanciada (pinos, frondosos, arbustos, rocas, flores); dónde está cada
  // una, su tamaño, su color y el apartarse para dejar ver a quien se sigue no cambian.
  function semilla(n) { let a = n >>> 0; return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function deformar(g0, k, sem) {
    const g = THREE.BufferGeometryUtils.mergeVertices(g0.index ? g0 : g0, 1e-4), r = semilla(sem), p = g.attributes.position, f = new Map();
    for (let i = 0; i < p.count; i++) { const key = p.getX(i).toFixed(3) + ',' + p.getY(i).toFixed(3) + ',' + p.getZ(i).toFixed(3);
      if (!f.has(key)) f.set(key, 1 + (r() - 0.5) * k); const m = f.get(key); p.setXYZ(i, p.getX(i) * m, p.getY(i) * (1 + (m - 1) * 0.5), p.getZ(i) * m); }
    g.computeVertexNormals(); return g;
  }
  function soloPosicion(g) { const n = new THREE.BufferGeometry(); n.setAttribute('position', g.attributes.position.clone()); if (g.index) n.setIndex(g.index.clone()); return n; }
  function unir(gs) { return THREE.BufferGeometryUtils.mergeBufferGeometries(gs.map(g => { const n = g.index ? g.toNonIndexed() : g; const o = new THREE.BufferGeometry();
    o.setAttribute('position', n.attributes.position); o.setAttribute('normal', n.attributes.normal); return o; })); }
  function piso(r, h, y, sem) {  // un piso de ramas de pino, con el borde caído
    const g = deformar(soloPosicion(new THREE.ConeGeometry(r, h, 14, 3).translate(0, y, 0)), 0.18, sem), p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { const rr = Math.hypot(p.getX(i), p.getZ(i)); p.setY(i, p.getY(i) - Math.pow(rr / r, 3) * h * 0.22 + Math.sin(Math.atan2(p.getZ(i), p.getX(i)) * 7 + sem) * 0.04 * rr / r); }
    g.computeVertexNormals(); return g;
  }
  let FORMAS = null;
  function formas() {
    if (FORMAS) return FORMAS;
    FORMAS = {
      // cono1 (r .52, alto 1.1, centro y 1.0) y cono2 (r .38, alto .85, centro y 1.55): dos pisos cada uno
      cono1: unir([piso(0.56, 0.7, 0.75, 1), piso(0.46, 0.65, 1.12, 2)]),
      cono2: unir([piso(0.38, 0.55, 1.45, 3), piso(0.26, 0.6, 1.8, 4)]),
      copa: unir([deformar(soloPosicion(new THREE.IcosahedronGeometry(0.42, 2).translate(0, 1.05, 0)), 0.3, 5), deformar(soloPosicion(new THREE.IcosahedronGeometry(0.32, 2).translate(0.28, 0.92, 0.1)), 0.3, 6),
        deformar(soloPosicion(new THREE.IcosahedronGeometry(0.3, 2).translate(-0.26, 0.98, -0.12)), 0.3, 7), deformar(soloPosicion(new THREE.IcosahedronGeometry(0.28, 2).translate(0.05, 1.32, 0)), 0.3, 8)]),
      arbusto: deformar(soloPosicion(new THREE.IcosahedronGeometry(0.3, 2).translate(0, 0.18, 0)), 0.35, 9),
      roca: deformar(soloPosicion(new THREE.IcosahedronGeometry(0.34, 2).scale(1, 0.7, 1).translate(0, 0.14, 0)), 0.4, 10),
      flor: deformar(soloPosicion(new THREE.IcosahedronGeometry(0.03, 1).scale(1, 0.6, 1).translate(0, 0.05, 0)), 0.2, 11),
    };
    return FORMAS;
  }
  // Las piezas del visor son copias sin nombre de tipo: se reconocen por su forma (número de vértices y tamaño).
  function firma(g) { g.computeBoundingBox(); const b = g.boundingBox; return g.attributes.position.count + '|' + [b.min.x, b.min.y, b.max.x, b.max.y, b.max.z].map(v => v.toFixed(3)).join(','); }
  let FIRMAS = null;
  function cual(g) {
    if (!FIRMAS) {  // las mismas piezas que crea plantar() en index.html
      FIRMAS = new Map([
        [firma(new THREE.ConeGeometry(.52, 1.1, 7).translate(0, 1.0, 0)), 'cono1'], [firma(new THREE.ConeGeometry(.38, .85, 7).translate(0, 1.55, 0)), 'cono2'],
        [firma(new THREE.IcosahedronGeometry(.55, 0).translate(0, 1.05, 0)), 'copa'], [firma(new THREE.IcosahedronGeometry(.3, 0).translate(0, .18, 0)), 'arbusto'],
        [firma(new THREE.DodecahedronGeometry(.34, 0).translate(0, .16, 0)), 'roca'], [firma(new THREE.IcosahedronGeometry(.055, 0)), 'flor']]);
    }
    const esfera = g.boundingSphere, f = firma(g); g.boundingSphere = esfera;
    return FIRMAS.get(f) || null;
  }
  function mejorarVegetacion() {
    if (!R.listo || !THREE.BufferGeometryUtils || typeof S === 'undefined') return;
    S.traverse(o => {
      if (!o.isInstancedMesh || o.userData.mejorado) return;
      o.userData.mejorado = true;
      const k = cual(o.geometry); if (!k) return;
      const esfera = o.geometry.boundingSphere, nueva = formas()[k];
      o.geometry = nueva.clone(); o.geometry.boundingSphere = esfera;  // conserva la esfera de su trozo (la cámara dibuja solo lo que ve)
      [].concat(o.material).forEach(m => { if (m.flatShading) { m.flatShading = false; m.needsUpdate = true; } });
    });
  }
  setInterval(mejorarVegetacion, 2000);

  // ---------- suelo con textura de detalle ----------
  let matHecho = null;
  const detalle = new THREE.TextureLoader().load('tex/detalle_suelo.jpg');
  detalle.wrapS = detalle.wrapT = THREE.RepeatWrapping; detalle.anisotropy = 8;
  function texturizarSuelo() {
    if (typeof terreno === 'undefined' || !terreno || terreno.material === matHecho) return;
    const mt = terreno.material, g = terreno.geometry, p = g.attributes.position, uv = new Float32Array(p.count * 2);
    for (let i = 0; i < p.count; i++) { uv[i * 2] = p.getX(i) / 3.2; uv[i * 2 + 1] = p.getZ(i) / 3.2; }
    const atr = new THREE.BufferAttribute(uv, 2);
    g.setAttribute('uv', atr);
    S.traverse(o => { if (o.isMesh && o.material === mt) o.geometry.setAttribute('uv', atr); });
    mt.map = detalle; mt.color.setScalar(1.45); mt.flatShading = false; mt.needsUpdate = true;  // la textura ronda el 60 % de brillo: se compensa
    matHecho = mt;
  }
  setInterval(texturizarSuelo, 1500);
})();
