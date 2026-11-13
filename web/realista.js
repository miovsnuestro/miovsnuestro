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
  const CUEROS = ['#4A3426', '#5B3F2A', '#3F382E', '#6A5A40', '#3B2F25', '#54402E'];  // pieles curtidas y fibras, más oscuras que la piel para que se distingan
  const SUPERIOR = /^(spine_0[123]|neck_01|Head|clavicle_[lr]|upperarm_[lr]|lowerarm_[lr]|hand_[lr]|(thumb|index|middle|ring|pinky)_0[123]_[lr])$/;
  const OCULTAR = /^(eyelashes|brows|tongue|teeth)$/;
  const VACIA = new THREE.BufferGeometry();
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
    u.cad.children.forEach(c => { if (c.isMesh && c !== u.torso) { c.scale.set(0.6, 0.5, 0.72); c.position.y = 0.05; } });  // cinturón del color de su gente
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
