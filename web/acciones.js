// Mío vs Nuestro · escenas de acción para los reels.
// Cuando la voz dice «Uxía vuelve de cazar con carne y pieles» o «Brais cambia madera por pescado con Noa»,
// la imagen tiene que enseñarlo: la cazadora con la carne en la mano y las pieles a la espalda, los dos frente a
// frente pasándose las cosas… Lo pide reels/fabrica.py con ?accion=…&con=…&prop=…&prop2=… y aquí se escenifica.
// Solo se usa en modo reel. Todo con piezas sencillas (como el resto del mundo) y lo mismo para las dos sociedades.

let ESC = null;

// ---------------- objetos que se ven en las manos ----------------
function PROP(tipo, lado) {
  const g = new THREE.Group(), add = (...m) => m.forEach(x => g.add(x));
  switch (tipo) {
    case 'carne': { const c = PZ(new THREE.DodecahedronGeometry(.1, 0), '#A8443A', 0, 0, 0); c.scale.set(1.25, .8, .9);
      const h = CIL(.018, .018, .26, '#EDE4D0', .02, 0, 0, 5); h.rotation.z = Math.PI / 2.4; add(c, h, PZ(new THREE.IcosahedronGeometry(.028, 0), '#EDE4D0', .13, .05, 0)); break; }
    case 'pieles': { const p = B(.34, .05, .24, '#8A5A36', 0, 0, 0); p.rotation.z = .15; add(p, B(.3, .04, .04, '#6E4426', 0, .04, .08), B(.3, .04, .04, '#6E4426', 0, .04, -.08)); break; }
    case 'madera': for (let i = 0; i < 3; i++) { const l = CIL(.045, .05, .5, i === 1 ? '#7A5232' : '#8A6038', (i - 1) * .09, i === 1 ? .07 : 0, 0, 6); l.rotation.z = Math.PI / 2; l.rotation.y = Math.PI / 2; add(l); } break;
    case 'piedra': add(PZ(new THREE.DodecahedronGeometry(.08, 0), '#8E8A80', -.05, 0, 0), PZ(new THREE.DodecahedronGeometry(.06, 0), '#A19C91', .07, .02, .02)); break;
    case 'pescado': { const c = PZ(new THREE.SphereGeometry(.07, 8, 6), '#9FB4C0', 0, 0, 0); c.scale.set(2.2, .8, .6);
      const t = PZ(new THREE.ConeGeometry(.06, .09, 4), '#7E95A2', -.19, 0, 0); t.rotation.z = Math.PI / 2; add(c, t, B(.02, .02, .02, '#1E1E1E', .11, .02, .03)); break; }
    case 'frutos': case 'comida': add(CIL(.12, .09, .12, '#B9A47A', 0, 0, 0, 8));
      for (let i = 0; i < 6; i++) add(PZ(new THREE.IcosahedronGeometry(.04, 0), ['#C8402E', '#E58A2B', '#7A2E5C'][i % 3], Math.cos(i) * .06, .08, Math.sin(i) * .06)); break;
    case 'fibra': for (let i = 0; i < 5; i++) { const f = B(.02, .36, .02, '#8AA35A', (i - 2) * .025, 0, 0); f.rotation.z = (i - 2) * .08; add(f); } add(B(.13, .03, .05, '#6E5A3A', 0, 0, 0)); break;
    case 'arcilla': add(PZ(new THREE.SphereGeometry(.1, 8, 6), '#B5653A', 0, 0, 0), CIL(.05, .06, .05, '#A55A33', 0, .09, 0, 8)); break;
    case 'metal': add(B(.18, .06, .08, '#9AA3A8', 0, 0, 0), B(.14, .03, .06, '#B7BEC2', 0, .045, 0)); break;
    case 'carbon': for (let i = 0; i < 3; i++) add(PZ(new THREE.DodecahedronGeometry(.05, 0), '#2A2A2A', (i - 1) * .07, i % 2 * .03, 0)); break;
    case 'bebe': { const c = CIL(.08, .07, .26, '#EDE4D0', 0, 0, 0, 8); c.rotation.z = Math.PI / 2; add(c, PZ(new THREE.IcosahedronGeometry(.07, 1), '#E0B48C', .16, .02, 0)); break; }
    case 'tablilla': add(B(.18, .24, .03, '#B5653A', 0, 0, 0), B(.12, .015, .01, '#7A3E22', 0, .05, .02), B(.12, .015, .01, '#7A3E22', 0, -.01, .02)); break;
    case 'brillo': { const m = new THREE.Mesh(new THREE.IcosahedronGeometry(.08, 0), new THREE.MeshBasicMaterial({ color: '#FFE08A' }));
      const h = new THREE.Mesh(new THREE.IcosahedronGeometry(.15, 1), new THREE.MeshBasicMaterial({ color: '#FFF3C4', transparent: true, opacity: .35, depthWrite: false }));
      add(m, h); g.userData.brilla = h; break; }
    case 'herramienta': add(B(.035, .4, .035, '#6E4A2C', 0, -.1, 0), PZ(new THREE.DodecahedronGeometry(.07, 0), '#8C8A86', 0, .12, 0)); break;
    case 'corazon': { const m = new THREE.MeshBasicMaterial({ color: '#FF6F91' });
      const a = new THREE.Mesh(new THREE.SphereGeometry(.07, 8, 6), m), b = new THREE.Mesh(new THREE.SphereGeometry(.07, 8, 6), m), c = new THREE.Mesh(new THREE.ConeGeometry(.1, .14, 8), m);
      a.position.set(-.05, .03, 0); b.position.set(.05, .03, 0); c.position.y = -.07; c.rotation.z = Math.PI; add(a, b, c); break; }
    case 'bandera': add(banderita(lado || 'A')); break;
    default: add(PZ(new THREE.IcosahedronGeometry(.1, 0), '#9A6B42', 0, 0, 0));  // un fardo
  }
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  g.scale.setScalar(1.35);  // que se lea bien en un plano vertical de móvil
  return g;
}
// Qué se ve en las manos para cada acción del día (escenas de «persona»)
const PROP_DE_ACCION = { recolectar: 'frutos', pescar: 'pescado', cazar: 'carne', talar: 'madera', picar_piedra: 'piedra',
  extraer_arcilla: 'arcilla', extraer_metal: 'metal', extraer_carbon: 'carbon', comer: 'frutos', depositar: 'frutos', tomar: 'frutos',
  leer: 'tablilla', inventar: 'brillo', fabricar: 'brillo', construir: 'madera', construir_refugio: 'madera', regalar: 'frutos',
  intercambiar: 'frutos', cultivar: 'fibra', asentarse: 'bandera', explorar: 'herramienta' };
// Tipo de suceso → cómo se escenifica
const MODO = { caza: 'volver', pescar: 'mostrar', trueque: 'cambio', intercambiar: 'cambio', trueque_rechazado: 'rechazo', regalo: 'dar', regalar: 'dar',
  robo: 'robar', robar: 'robar', habla: 'charla', hablar: 'charla', 'enseñanza': 'ensenar', 'enseñar': 'ensenar', ensenar: 'ensenar', pareja: 'pareja',
  cortejar: 'pareja', refugio: 'obra', construir_refugio: 'obra', construir: 'obra', construccion_nueva: 'obra', invento: 'invento',
  invento_inedito: 'invento', objeto_nuevo: 'invento', inventar: 'invento', fabricar: 'invento', nombre_nuevo: 'invento', nacimiento: 'bebe',
  'almacén': 'cargar', depositar: 'cargar', tomar: 'cargar', lectura: 'leer', duda: 'leer', leer: 'leer', territorio: 'reclamar',
  asentarse: 'reclamar', 'exploración': 'explorar', explorar: 'explorar' };
const DOS = new Set(['cambio', 'rechazo', 'dar', 'robar', 'charla', 'ensenar', 'pareja', 'bebe']);

function mano(u, lado) {  // soporte en la mano que no gira con el brazo (el objeto se queda derecho)
  const k = lado === 'I' ? 'sopI' : 'sopD';
  if (!u[k]) { const s = new THREE.Group(); s.position.set(0, -.36, .06); (lado === 'I' ? u.bI : u.bD).add(s); u[k] = s; }
  return u[k];
}
function sostener(g, tipo, lado) { const u = g.userData, s = mano(u, lado); while (s.children.length) s.remove(s.children[0]); if (tipo) s.add(PROP(tipo, u.a.lado)); return s; }
function libre(p) { return suelo(p.x, p.z) > NIVEL + .12; }

function prepararEscena(g) {
  const tipo = q.get('accion'); if (!tipo || ESC) return;
  const modo = MODO[tipo] || (PROP_DE_ACCION[tipo] ? 'tarea' : null); if (!modo) return;
  const u = g.userData;
  ESC = { tipo, modo, foco: g, otro: null, t: 0, dur: +(q.get('dur') || 6), prop: q.get('prop') || PROP_DE_ACCION[tipo] || null, prop2: q.get('prop2') || null, volando: null, hecho: {} };
  // los dos frente a frente, a un paso, en suelo firme
  if (DOS.has(modo)) {
    let o = gente.get(+q.get('con'));
    if (!o || o === g) { const cand = [...gente.values()].filter(x => x !== g && x.userData.a.lado === u.a.lado && x.userData.a.edad >= 14);
      cand.sort((a, b) => a.position.distanceTo(g.position) - b.position.distanceTo(g.position)); o = cand[0]; }
    if (o) {
      let ang = hash(u.a.id, 7) * Math.PI * 2, pos = null;
      for (let k = 0; k < 16 && !pos; k++) { const a = ang + k * Math.PI / 8, c = new THREE.Vector3(g.position.x + Math.sin(a) * 1.05, 0, g.position.z + Math.cos(a) * 1.05); if (libre(c)) { pos = c; ang = a; } }
      if (pos) {
        o.position.copy(pos); ESC.otro = o;
        // frente a frente, pero un poco girados hacia la cámara para que se les vea la cara y las manos
        const yc = yawEscena(), gira = (a, h) => a + .38 * Math.atan2(Math.sin(h - a), Math.cos(h - a));
        g.rotation.y = gira(ang, yc); o.rotation.y = gira(ang + Math.PI, yc); ESC.yaw = yc;
        for (const x of [g, o]) { const v = x.userData; v.dest = null; v.base = x.position.clone(); v.espera = 1e9; v.a = { ...v.a, accion: 'hablar' }; }
      }
    }
  }
  if (!ESC.otro) { u.dest = null; u.base = g.position.clone(); u.espera = 1e9; }
  // los que caminan: hacia su pueblo (vuelve de cazar, carga al almacén) o hacia fuera (explora, reclama)
  if (modo === 'volver' || modo === 'cargar' || modo === 'explorar' || modo === 'reclamar') {
    const pl = plazas[u.a.lado], hacia = pl ? new THREE.Vector3(X(pl[0]), 0, Z(pl[1])) : g.position.clone().add(new THREE.Vector3(1, 0, 0));
    const dir = hacia.sub(g.position); dir.y = 0; if (dir.length() < .1) dir.set(1, 0, 0); dir.normalize(); if (modo === 'explorar' || modo === 'reclamar') dir.multiplyScalar(-1);
    const meta = g.position.clone().addScaledVector(dir, Math.min(3.2, ESC.dur * .5));
    if (libre(meta)) { u.dest = meta; g.rotation.y = Math.atan2(dir.x, dir.z); }
  }
  // lo que lleva cada uno desde el principio
  const p1 = ESC.prop;
  if (modo === 'volver') { sostener(g, 'carne', 'I'); const pi = PROP('pieles'); pi.position.set(0, .2, -.14); pi.rotation.x = 1.3; pi.scale.setScalar(1.1); u.torso.add(pi); ESC.espalda = pi; }
  else if (modo === 'cambio' || modo === 'rechazo') { sostener(g, p1 || 'frutos', 'D'); if (ESC.otro) sostener(ESC.otro, ESC.prop2 || 'madera', 'D'); }
  else if (modo === 'dar') sostener(g, p1 || 'frutos', 'D');
  else if (modo === 'robar') { if (ESC.otro) sostener(ESC.otro, p1 || 'frutos', 'D'); }
  else if (modo === 'ensenar') sostener(g, p1 || 'herramienta', 'D');
  else if (modo === 'bebe') sostener(g, 'bebe', 'D');
  else if (modo === 'cargar' || modo === 'mostrar' || modo === 'tarea' || modo === 'explorar') { if (p1 && p1 !== 'brillo' && p1 !== 'bandera' && !['talar', 'picar_piedra'].includes(tipo)) sostener(g, p1, 'D'); }
  else if (modo === 'leer') sostener(g, 'tablilla', 'I');
  else if (modo === 'obra') { const m = PROP('madera'); m.position.copy(g.position).add(new THREE.Vector3(Math.sin(g.rotation.y) * .55, suelo(g.position.x, g.position.z) + .06, Math.cos(g.rotation.y) * .55)); S.add(m); }
  if (tipo === 'talar' || tipo === 'picar_piedra') { const m = PROP(tipo === 'talar' ? 'madera' : 'piedra'); m.position.copy(g.position).add(new THREE.Vector3(Math.sin(g.rotation.y + 1.2) * .6, suelo(g.position.x, g.position.z) + .06, Math.cos(g.rotation.y + 1.2) * .6)); S.add(m); }
}

// Centro y ángulo de cámara: con dos personas, de lado para que se vea lo que pasa entre ellos
function centroEscena() { if (!ESC || !ESC.otro) return null; return ESC.foco.position.clone().add(ESC.otro.position).multiplyScalar(.5); }
function yawEscena() { if (ESC && ESC.yaw !== undefined) return ESC.yaw; if (!ESC || !ESC.otro) return null; const d = ESC.otro.position.clone().sub(ESC.foco.position); const base = Math.atan2(d.x, d.z) + Math.PI / 2;
  // de los dos lados posibles, el que tenga menos cosas delante
  const a = angDespejado(centroEscena()); const dd = x => Math.abs(Math.atan2(Math.sin(x - a), Math.cos(x - a))); return dd(base) <= dd(base + Math.PI) ? base : base + Math.PI; }

// Mover un objeto de la mano de uno a la del otro, en arco
function pasar(de, a, tipo, ladoDe, ladoA) {
  const sd = mano(de.userData, ladoDe), pa = new THREE.Vector3(); sd.getWorldPosition(pa);
  while (sd.children.length) sd.remove(sd.children[0]);
  const obj = PROP(tipo); obj.position.copy(pa); S.add(obj);
  return { obj, desde: pa, a, ladoA, tipo, k: 0 };
}
function volar(v, dt, dur) {
  v.k = Math.min(1, v.k + dt / dur);
  const dst = new THREE.Vector3(); mano(v.a.userData, v.ladoA).getWorldPosition(dst);
  v.obj.position.lerpVectors(v.desde, dst, v.k); v.obj.position.y += Math.sin(v.k * Math.PI) * .35; v.obj.rotation.y += dt * 4;
  if (v.k >= 1) { S.remove(v.obj); sostener(v.a, v.tipo, v.ladoA); return true; }
  return false;
}

// Se llama al final de animarPersona: corrige la postura para que se vea la acción narrada
function animarEscena(g, dt) {
  if (!ESC) return;
  const esFoco = g === ESC.foco, esOtro = g === ESC.otro; if (!esFoco && !esOtro) return;
  const u = g.userData, m = ESC.modo;
  if (esFoco) ESC.t += dt;
  const k = ESC.t / ESC.dur, f = ESC.t;
  for (const s of [u.sopD, u.sopI]) if (s) { s.rotation.x = -(s.parent.rotation.x); }  // el objeto, siempre derecho
  if (u.manoD && ((u.sopD && u.sopD.children.length) || ESC.otro)) u.manoD.visible = false;
  if (u.manoI && ((u.sopI && u.sopI.children.length) || ESC.otro)) u.manoI.visible = false;
  if (!u.manoD && u.herr && ESC.otro) u.herr.visible = false;
  const andando = !!u.dest;
  if (m === 'volver') { if (esFoco) { u.bI.rotation.x = andando ? -.7 : -1.25 + Math.sin(f * 2) * .08; u.bI.rotation.z = -.15; if (!andando) { u.cuello.rotation.x = -.15; } } }
  else if (m === 'mostrar') { u.bD.rotation.x = -1.6 - suave(.2, .5, k) * .8; u.cuello.rotation.x = -.2; }
  else if (m === 'cambio' || m === 'rechazo' || m === 'dar' || m === 'robar') {
    const ofrece = suave(.15, .4, k) * (1 - suave(.7, .9, k));
    if (m === 'cambio' || (m === 'dar' && esFoco) || (m === 'robar' && esOtro) || (m === 'rechazo')) u.bD.rotation.x = -.3 - ofrece * 1.1;
    if (m === 'rechazo' && esOtro && k > .5) { u.cuello.rotation.y = Math.sin(f * 7) * .35; u.bD.rotation.x = -.3; }
    if (m === 'robar' && esFoco) { u.bD.rotation.x = -.3 - suave(.3, .42, k) * 1.2 * (1 - suave(.55, .65, k)); }
    if (esFoco && !ESC.hecho.pase && k > .45 && m !== 'rechazo' && ESC.otro) {
      ESC.hecho.pase = true; ESC.vuelos = [];
      if (m === 'cambio') ESC.vuelos.push(pasar(g, ESC.otro, ESC.prop || 'frutos', 'D', 'I'), pasar(ESC.otro, g, ESC.prop2 || 'madera', 'D', 'I'));
      if (m === 'dar') ESC.vuelos.push(pasar(g, ESC.otro, ESC.prop || 'frutos', 'D', 'D'));
      if (m === 'robar') ESC.vuelos.push(pasar(ESC.otro, g, ESC.prop || 'frutos', 'D', 'D'));
    }
    if (esFoco && ESC.vuelos) ESC.vuelos = ESC.vuelos.filter(v => !volar(v, dt, ESC.dur * .14));
    if (k > .62) { u.bI.rotation.x = m === 'robar' && esOtro ? -.2 : -.9; u.cuello.rotation.x = (m === 'cambio' || (m === 'dar' && esOtro)) ? Math.max(0, Math.sin(f * 4)) * .25 : 0; }
    if (m === 'robar' && esFoco && k > .66 && !ESC.hecho.huye) { ESC.hecho.huye = true; const d = g.position.clone().sub(ESC.otro.position).setY(0).normalize(); const meta = g.position.clone().addScaledVector(d, 2.2); if (libre(meta)) u.dest = meta; }
  }
  else if (m === 'charla' || m === 'ensenar') {
    const habla = Math.floor(f / 1.3) % 2 === 0 ? esFoco : esOtro;
    if (habla) { u.bD.rotation.x = -.6 + Math.sin(f * 5) * .35; u.bD.rotation.z = .25; u.bI.rotation.x = -.3 + Math.sin(f * 4 + 1) * .2; }
    else { u.cuello.rotation.x = Math.max(0, Math.sin(f * 3)) * .18; u.bD.rotation.x = 0; }
    if (m === 'ensenar') { if (esFoco) { u.bD.rotation.x = -1.3 - Math.sin(f * 2) * .3; } else if (k > .55) { if (!ESC.hecho.copia) { ESC.hecho.copia = true; sostener(g, ESC.prop || 'herramienta', 'D'); } u.bD.rotation.x = -1.1 - Math.sin(f * 2 + 1) * .3; } }
  }
  else if (m === 'pareja') {
    const junto = suave(.35, .6, k);
    if (esOtro && ESC.otro) { const c = ESC.foco.position.clone().add(ESC.otro.position).multiplyScalar(.5), d = g.position.clone().sub(c).setY(0); if (d.length() > .38) g.position.addScaledVector(d.normalize(), -dt * .25 * junto); }
    u.bD.rotation.x = -.9 * junto; u.bI.rotation.x = -.5 * junto; u.cuello.rotation.x = -.1 * junto;
    if (esFoco && k > .62 && !ESC.hecho.corazon) { ESC.hecho.corazon = true; const h = PROP('corazon'); h.scale.setScalar(2); const c = centroEscena() || g.position; h.position.set(c.x, suelo(c.x, c.z) + 1.55, c.z); S.add(h); ESC.corazon = h; }
    if (esFoco && ESC.corazon) { ESC.corazon.position.y += dt * .12; ESC.corazon.rotation.y += dt * 1.5; ESC.corazon.scale.setScalar(2 * (1 + Math.sin(f * 6) * .08)); }
  }
  else if (m === 'bebe') { if (esFoco) { u.bD.rotation.x = -1.2; u.bI.rotation.x = -1.2; u.bD.rotation.z = .35; u.bI.rotation.z = -.35; u.cuello.rotation.x = .35; u.cad.position.y = .5 + Math.sin(f * 2) * .01; } else { u.cuello.rotation.x = .3; u.bI.rotation.x = -.4; } }
  else if (m === 'obra') { const s = (Math.sin(f * 5) + 1) / 2; u.bD.rotation.x = -2.4 + s * 1.9; u.bI.rotation.x = -1.4 + s * .9; u.torso.rotation.x = s * .25; }
  else if (m === 'invento') {
    if (k < .55) { u.cuello.rotation.x = .4; u.bD.rotation.x = -1 + Math.sin(f * 6) * .2; u.bI.rotation.x = -.95; u.torso.rotation.x = .2; }
    else { if (!ESC.hecho.brillo) { ESC.hecho.brillo = true; sostener(g, 'brillo', 'D'); } const s = suave(.55, .7, k); u.bD.rotation.x = -1 - s * 1.6; u.cuello.rotation.x = -.3 * s; u.bI.rotation.x = -.2; }
    const b = u.sopD && u.sopD.children[0] && u.sopD.children[0].userData.brilla; if (b) { b.scale.setScalar(1 + Math.sin(f * 8) * .25); b.material.opacity = .25 + Math.sin(f * 8) * .12; }
  }
  else if (m === 'cargar') { u.bD.rotation.x = andando ? -.5 : -.8; u.bI.rotation.x = andando ? -.5 : -.8; }
  else if (m === 'leer') { u.bI.rotation.x = -1.25; u.bD.rotation.x = -1.0; u.cuello.rotation.x = .45; }
  else if (m === 'reclamar' && !andando && !ESC.hecho.bandera) { ESC.hecho.bandera = true; const b = banderita(u.a.lado); b.scale.setScalar(1.4); b.position.set(g.position.x + Math.sin(g.rotation.y) * .5, suelo(g.position.x, g.position.z), g.position.z + Math.cos(g.rotation.y) * .5); S.add(b); }
  else if (m === 'tarea' && ['recolectar', 'comer', 'cultivar'].includes(ESC.tipo)) { /* la postura de recoger ya la pone animarPersona; solo se ve lo que lleva */ }
}
