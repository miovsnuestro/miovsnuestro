// Mío vs Nuestro · todo lo que las sociedades hacen, visible en el mundo.
// Cada construcción es una pieza en su sitio (4 casas = 4 casas), cada objeto lo lleva quien lo tiene,
// la ropa tiene el color que eligieron, los campos se ven arados y el bosque cortado se queda en claro.
// El estilo de cada lado depende SOLO de lo que ha logrado esa sociedad (su propia época).
// Las piezas se dibujan aquí con formas simples; si en web/modelos/indice.json hay un modelo 3D (GLB)
// para una clave («estructura:molino», «objeto:hacha»…), se usa ese. Un modelo vale para los dos lados.
// Este archivo solo define funciones: las llama index.html cuando ya tiene el mundo.

const GIRAN = [], FLOTAN = [];
let firmaObras = '', firmaTala = '', tocones = null;

// ---------------- modelos 3D subidos (GLB) ----------------
let GLB = {}, glbListo = {}, glbPidiendo = {}, glbVersion = 0;
Promise.all(['indice', 'subidos'].map(n => fetch('modelos/' + n + '.json?t=' + Date.now()).then(r => r.ok ? r.json() : {}).catch(() => ({})))).then(([a, b]) => {
  GLB = Object.assign({}, a || {}, b || {});
  if (Object.keys(GLB).length) { const s = document.createElement('script'); s.src = 'GLTFLoader.js'; s.onload = () => { firmaObras = ''; glbVersion++; if (est && est.obras) construirObras(est); }; document.head.appendChild(s); }
}).catch(() => {});
function modeloGLB(clave, altura) {
  const ruta = GLB[clave]; if (!ruta || !THREE.GLTFLoader) return null;
  if (glbListo[clave]) { const g = glbListo[clave].clone(true); g.scale.multiplyScalar(altura || 1); return g; }
  if (!glbPidiendo[clave]) {
    glbPidiendo[clave] = true;
    new THREE.GLTFLoader().load('modelos/' + (typeof ruta === 'string' ? ruta : ruta.archivo), gl => {
      const m = gl.scene, caja = new THREE.Box3().setFromObject(m), tam = caja.getSize(new THREE.Vector3());
      const k = 1 / Math.max(tam.y, tam.x * .6, tam.z * .6, .001); m.scale.setScalar(k);
      m.position.y = -caja.min.y * k; m.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
      const g = new THREE.Group(); g.add(m); glbListo[clave] = g; glbVersion++; firmaObras = ''; if (est && est.obras) construirObras(est);
    }, undefined, () => {});
  }
  return null;
}

// ---------------- piezas de construcción ----------------
const PZ = (geo, c, x = 0, y = 0, z = 0) => { const m = new THREE.Mesh(geo, MF(c)); m.position.set(x, y, z); return m; };
const B = (w, h, d, c, x, y, z) => PZ(new THREE.BoxGeometry(w, h, d), c, x, y, z);
const CIL = (r1, r2, h, c, x, y, z, n = 8) => PZ(new THREE.CylinderGeometry(r1, r2, h, n), c, x, y, z);
function sombra(g) { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; }

function casaEpoca(ep, lado) {
  if (ep === 'prehistoria' || ep === 'aldeas') return casa(ep, lado);
  if (ep === 'metal') return casa('piedra', lado);
  const g = new THREE.Group(), techo = lado === 'A' ? '#2F8A6A' : '#C8613A';
  if (ep === 'industrial') {
    g.add(B(1.6, 1.3, 1.3, '#A0563B', 0, .65, 0), B(1.7, .12, 1.4, techo, 0, 1.36, 0), B(.2, .7, .2, '#6B3A2A', .5, 1.7, -.3));
    for (const s of [-1, 1]) g.add(B(.3, .34, .04, '#6E8796', s * .45, .78, .66));
    g.add(B(.34, .6, .04, '#4A2E1E', 0, .3, .66));
  } else {  // moderna y espacial
    g.add(B(1.8, 1.1, 1.4, '#ECEAE4', 0, .55, 0), B(1.9, .1, 1.5, techo, 0, 1.15, 0), B(1.2, .55, .04, '#7FA6BC', -.2, .62, .71));
    g.add(B(.32, .7, .04, '#5A5A5A', .62, .35, .71));
    if (ep === 'espacial') g.add(PZ(new THREE.SphereGeometry(.22, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), '#CFD6DC', -.5, 1.2, -.3));
  }
  g.scale.setScalar(1.3); return sombra(g);
}
function almacen(lado) { const g = new THREE.Group(); g.add(B(1.6, .9, 1.2, '#9A6B42', 0, .45, 0));
  const t = PZ(new THREE.CylinderGeometry(.62, .62, 1.62, 6, 1, false, 0, Math.PI), '#7A5232', 0, .9, 0); t.rotation.z = Math.PI / 2; g.add(t);
  g.add(B(.5, .6, .04, '#5A3A20', 0, .3, .61), B(.5, .06, .05, COLOR[lado], 0, .64, .62)); return sombra(g); }
function granero(lado) { const g = almacen(lado); g.scale.set(1, 1.25, 1); return g; }
function escuela(lado) { const g = new THREE.Group(); g.add(B(2.2, .8, 1.1, '#C9A878', 0, .4, 0));
  const t = PZ(new THREE.ConeGeometry(1.3, .6, 4), '#9A7A4A', 0, 1.1, 0); t.rotation.y = Math.PI / 4; t.scale.set(1.25, 1, .7); g.add(t);
  for (const x of [-.6, 0, .6]) g.add(B(.26, .24, .04, '#6E8796', x, .5, .56));
  g.add(CIL(.03, .03, 1, '#6E4A2C', .9, 1.3, 0, 5), B(.3, .2, .02, COLOR[lado], 1.05, 1.68, 0)); return sombra(g); }
function mercado(lado) { const g = new THREE.Group();
  for (const [x, z] of [[-.6, -.45], [.6, -.45], [-.6, .45], [.6, .45]]) g.add(CIL(.04, .04, 1.1, '#6E4A2C', x, .55, z, 5));
  for (let i = 0; i < 5; i++) g.add(B(.28, .05, 1.05, i % 2 ? '#EDEAE2' : COLOR[lado], -.56 + i * .28, 1.12, 0));
  g.add(B(1.3, .08, .5, '#8A6038', 0, .55, .1));
  for (let i = 0; i < 4; i++) g.add(PZ(new THREE.IcosahedronGeometry(.08, 0), ['#C0392B', '#E5B92E', '#3E8E41', '#E07B24'][i], -.45 + i * .3, .66, .1));
  g.add(B(.34, .28, .3, '#9A6B42', .75, .14, -.3), B(.3, .24, .3, '#9A6B42', -.8, .12, .4)); return sombra(g); }
function molino() { const g = new THREE.Group(); g.add(CIL(.32, .48, 1.8, '#D8D2C2', 0, .9, 0, 8), PZ(new THREE.ConeGeometry(.42, .5, 8), '#8A6038', 0, 2.05, 0));
  const aspas = new THREE.Group(); aspas.position.set(0, 1.6, .5);
  for (let i = 0; i < 4; i++) { const a = B(.14, 1.1, .02, '#EDEAE2', 0, .6, 0), p = new THREE.Group(); p.add(a); p.rotation.z = i * Math.PI / 2; aspas.add(p); }
  g.add(aspas); GIRAN.push(aspas); return sombra(g); }
function torre(lado) { const g = new THREE.Group(); g.add(CIL(.4, .5, 2.4, '#8E8A80', 0, 1.2, 0, 7), CIL(.55, .55, .2, '#7E7A70', 0, 2.5, 0, 7), B(.3, .2, .02, COLOR[lado], .2, 2.9, 0)); return sombra(g); }
function observatorio() { const g = new THREE.Group(); g.add(CIL(.55, .6, 1.2, '#CFC8B8', 0, .6, 0, 10), PZ(new THREE.SphereGeometry(.56, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2), '#9AA3A8', 0, 1.2, 0));
  const tub = CIL(.07, .09, .6, '#4A4A4A', .2, 1.6, 0, 6); tub.rotation.z = -.7; g.add(tub); return sombra(g); }
function fabrica(lado) { const g = new THREE.Group(); g.add(B(2.4, 1.2, 1.5, '#8E5A44', 0, .6, 0));
  for (let i = 0; i < 3; i++) { const d = PZ(new THREE.ConeGeometry(.5, .5, 4), '#6B4A3A', -.8 + i * .8, 1.45, 0); d.rotation.y = Math.PI / 4; d.scale.set(1, 1, 1.9); g.add(d); }
  g.add(CIL(.16, .2, 1.6, '#5A4A44', .9, 2, -.4, 7), B(.6, .08, .05, COLOR[lado], -.8, .9, .76)); return sombra(g); }
function camino() { const g = new THREE.Group(); for (let i = 0; i < 6; i++) { const p = PZ(new THREE.CylinderGeometry(.16 + hash(i, 3) * .08, .18, .05, 6), '#9A958A', (i - 2.5) * .18, .03, (hash(i, 5) - .5) * .3); g.add(p); } g.traverse(o => { if (o.isMesh) o.receiveShadow = true; }); return g; }
function puente() { const g = new THREE.Group(); g.add(B(.7, .08, 2.2, '#8A6038', 0, .25, 0)); for (const s of [-1, 1]) for (const z of [-1, 0, 1]) g.add(CIL(.03, .03, .4, '#5A3A20', s * .33, .35, z, 4)); return sombra(g); }
function maquina() { const g = new THREE.Group(); g.add(B(.9, .6, .7, '#6E7377', 0, .3, 0));
  const r = PZ(new THREE.TorusGeometry(.28, .06, 6, 10), '#9AA3A8', 0, .75, .1); g.add(r); GIRAN.push(r); g.add(CIL(.06, .06, .5, '#4A4A4A', .3, .85, -.2, 6)); return sombra(g); }
function globo(lado) { const g = new THREE.Group(), arriba = new THREE.Group();
  arriba.add(PZ(new THREE.SphereGeometry(.7, 12, 10), '#E5B92E', 0, 2.2, 0), B(.36, .26, .36, '#8A6038', 0, 1.05, 0));
  for (const [x, z] of [[-.15, -.15], [.15, -.15], [-.15, .15], [.15, .15]]) arriba.add(CIL(.01, .01, .8, '#5A3A20', x * 2, 1.55, z * 2, 3));
  arriba.add(B(.2, .3, .02, COLOR[lado], 0, 2.2, .71)); g.add(arriba); FLOTAN.push(arriba); return sombra(g); }
function cohete(lado) { const g = new THREE.Group(); g.add(CIL(.28, .32, 2.4, '#ECEAE4', 0, 1.5, 0, 10), PZ(new THREE.ConeGeometry(.28, .7, 10), COLOR[lado], 0, 3.05, 0));
  for (let i = 0; i < 3; i++) { const a = B(.04, .5, .4, '#9AA3A8', 0, .5, 0); const p = new THREE.Group(); a.position.z = .38; p.add(a); p.rotation.y = i * 2.09; g.add(p); }
  g.add(B(1.2, .2, 1.2, '#6E7377', 0, .1, 0)); return sombra(g); }
function enfermeria(lado) { const g = casaEpoca('metal', lado); g.add(PZ(new THREE.IcosahedronGeometry(.14, 0), '#3E8E41', 0, 1.15, .9)); return g; }
function monumento(lado) { const g = new THREE.Group(); g.add(B(.45, 1.6, .3, '#8E8A80', 0, .8, 0), B(.7, .2, .5, '#7E7A70', 0, .1, 0), B(.46, .08, .31, COLOR[lado], 0, 1.4, 0)); return sombra(g); }
function horno() { const g = new THREE.Group(); g.add(PZ(new THREE.SphereGeometry(.5, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), '#B5653A'), B(.25, .22, .05, '#2A1A10', 0, .12, .48)); return sombra(g); }
function pozo() { const g = new THREE.Group(); g.add(CIL(.4, .42, .4, '#8E8A80', 0, .2, 0, 10), CIL(.32, .32, .02, '#3A5A70', 0, .38, 0, 10));
  for (const s of [-1, 1]) g.add(CIL(.03, .03, .8, '#6E4A2C', s * .36, .75, 0, 4)); g.add(B(.9, .05, .5, '#8A6038', 0, 1.15, 0)); return sombra(g); }
function muralla() { const g = new THREE.Group(); g.add(B(2, .9, .4, '#8E8A80', 0, .45, 0)); for (let i = 0; i < 4; i++) g.add(B(.3, .2, .42, '#7E7A70', -.8 + i * .53, 1, 0)); return sombra(g); }
function generica(lado, cat) {  // algo que el catálogo aún no sabe dibujar: una pieza neutra mientras llega el modelo
  const g = new THREE.Group();
  for (const [x, z] of [[-.4, -.4], [.4, -.4], [-.4, .4], [.4, .4]]) g.add(CIL(.03, .03, .8, '#6E4A2C', x, .4, z, 4));
  g.add(B(.95, .05, .95, '#D8C7A0', 0, .82, 0), B(.4, .4, .4, '#9A6B42', 0, .2, 0), B(.42, .06, .42, COLOR[lado], 0, .42, 0)); return sombra(g); }

const RADIO = { casa: 1.3, almacen: 1, granero: 1, escuela: 1.3, mercado: .9, molino: .6, torre: .6, observatorio: .7, fabrica: 1.5, maquina: .6,
  cohete: .7, enfermeria: 1.3, monumento: .5, horno: .5, pozo: .5, muralla: 1, taller: .9, corral: 1.4, hoguera: .75, carro: .8 };
const radioDe = (t, ep) => t !== 'casa' ? (RADIO[t] || .4) : ep === 'prehistoria' ? 1.05 : ep === 'aldeas' || ep === 'metal' ? 1.35 : 1.7;
function pieza(e, ep) {
  const l = e.lado, t = e.tipo;
  const glb = modeloGLB(e.modelo && e.modelo !== 'nuevo' ? e.modelo : 'estructura:' + t, t === 'casa' ? 1.8 : 1.4);
  if (glb) return glb;
  switch (t) {
    case 'casa': return casaEpoca(ep, l);
    case 'hoguera': { const h = hoguera(); if (fuegos.length > 6) { const f = fuegos[fuegos.length - 1]; f.luz.visible = false; } return h; }
    case 'corral': return corral(); case 'taller': return taller(); case 'carro': return carro(); case 'barco': return balsa();
    case 'almacen': return almacen(l); case 'granero': return granero(l); case 'escuela': return escuela(l); case 'mercado': return mercado(l);
    case 'molino': return molino(); case 'torre': return torre(l); case 'observatorio': return observatorio(); case 'fabrica': return fabrica(l);
    case 'camino': return camino(); case 'puente': return puente(); case 'maquina': return maquina(); case 'globo': return globo(l);
    case 'cohete': return cohete(l); case 'enfermeria': return enfermeria(l); case 'monumento': return monumento(l);
    case 'horno': return horno(); case 'pozo': return pozo(); case 'muralla': return muralla();
    default: return generica(l, e.categoria);
  }
}
function banderita(lado) { const g = new THREE.Group(); g.add(CIL(.02, .02, .9, '#6E4A2C', 0, .45, 0, 4), B(.28, .16, .01, COLOR[lado], .14, .82, 0)); return g; }
const estiloDe = (e, l) => (e.sociedades[l] && e.sociedades[l].epoca) || e.epoca || 'prehistoria';

// ---------------- campos arados ----------------
function campos(lista, ocupado) {
  const g = new THREE.Group(), tierra = [], surcos = [];
  for (const [x, y, l] of lista) { if (ocupado.has(x + ',' + y)) continue; tierra.push([x + .5, y + .5]); for (let i = 0; i < 4; i++) surcos.push([x + .5, y + .14 + i * .24, l]); }
  const d = new THREE.Object3D(), c = new THREE.Color();
  const im1 = new THREE.InstancedMesh(new THREE.BoxGeometry(.96, .05, .96), MF('#7A5A3A'), Math.max(1, tierra.length));
  tierra.forEach((p, i) => { d.position.set(X(p[0]), Math.max(suelo(X(p[0]), Z(p[1])), 0) + .02, Z(p[1])); d.rotation.set(0, 0, 0); d.scale.set(1, 1, 1); d.updateMatrix(); im1.setMatrixAt(i, d.matrix); });
  im1.count = tierra.length; im1.receiveShadow = true;
  const im2 = new THREE.InstancedMesh(new THREE.BoxGeometry(.86, .14, .1), new THREE.MeshPhongMaterial({ color: '#fff', flatShading: true, shininess: 0 }), Math.max(1, surcos.length));
  surcos.forEach((p, i) => { d.position.set(X(p[0]), Math.max(suelo(X(p[0]), Z(p[1])), 0) + .09, Z(p[1])); d.updateMatrix(); im2.setMatrixAt(i, d.matrix); c.set(hash(Math.round(p[0] * 9), Math.round(p[1] * 9)) < .5 ? '#8DBA4A' : '#B8C45A'); im2.setColorAt(i, c); });
  im2.count = surcos.length; im2.castShadow = true;
  for (const im of [im1, im2]) { im.geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e4); g.add(im); }
  return g;
}

// ---------------- bosque cortado ----------------
function aplicarTala(lista) {
  const f = JSON.stringify(lista || []); if (f === firmaTala) return false; firmaTala = f;
  restaurarVista();
  const corte = new Map(); for (const [x, y, n] of (lista || [])) corte.set(x + ',' + y, Math.min(1, n / 6));
  const tocon = [];
  for (const im of ocultables) {
    if (!im.userData.arbol) continue;
    if (!im.userData.orig) im.userData.orig = Float32Array.from(im.instanceMatrix.array);
    const l = im.userData.lista, o = im.userData.orig, a = im.instanceMatrix.array;
    for (let i = 0; i < l.length; i++) {
      const p = l[i], k = Math.floor(p[0]) + ',' + Math.floor(p[1]), fr = corte.get(k) || 0;
      const cortado = fr > 0 && hash(Math.round(p[0] * 97), Math.round(p[1] * 89)) < fr;
      for (let j = 0; j < 16; j++) a[i * 16 + j] = cortado ? _cero.elements[j] : o[i * 16 + j];
      if (cortado && im.userData.tronco) tocon.push(p);
    }
    im.instanceMatrix.needsUpdate = true;
  }
  if (tocones) { tocones.parent && tocones.parent.remove(tocones); tocones = null; }
  if (tocon.length) {
    tocones = new THREE.InstancedMesh(new THREE.CylinderGeometry(.1, .12, .16, 6), MF('#7A5232'), tocon.length); const d = new THREE.Object3D();
    tocon.forEach((p, i) => { d.position.set(X(p[0]), suelo(X(p[0]), Z(p[1])) + .08, Z(p[1])); d.scale.setScalar(p[2]); d.updateMatrix(); tocones.setMatrixAt(i, d.matrix); });
    tocones.geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e4); tocones.castShadow = true; S.add(tocones);
  }
  return true;
}

// ---------------- el pueblo de cada sociedad, pieza a pieza ----------------
function construirObras(e) {
  const obras = e.obras.estructuras || [];
  const firma = ['A', 'B'].map(l => estiloDe(e, l)).join() + '|' + obras.map(o => o.id + o.tipo + o.x + ',' + o.y).join(';') + '|' + (e.obras.campos || []).length + '|' + Object.keys(glbListo).length;
  const talaCambia = aplicarTala(e.talado);
  if (firma === firmaObras && !talaCambia) return; firmaObras = firma;
  pueblos.clear(); fuegos.length = 0; banderas.length = 0; obstaculos.length = 0; GIRAN.length = 0; FLOTAN.length = 0;
  const listaCampos = (e.obras.campos || []).concat(obras.filter(o => o.tipo === 'campo').map(o => [o.x, o.y, o.lado]));
  const ocupado = new Set(obras.filter(o => o.tipo !== 'campo').map(o => o.x + ',' + o.y));
  for (const l of 'AB') {
    const casas = obras.filter(o => o.lado === l && o.tipo === 'casa');
    let pu, pv;
    if (casas.length) {  // la plaza está en el pueblo más grande (el núcleo con más casas juntas)
      const cerca = c => casas.filter(d => Math.abs(d.x - c.x) + Math.abs(d.y - c.y) <= 8);
      const nucleo = cerca(casas.reduce((m, c) => cerca(c).length > cerca(m).length ? c : m, casas[0]));
      pu = nucleo.reduce((s, c) => s + c.x + .5, 0) / nucleo.length; pv = nucleo.reduce((s, c) => s + c.y + .5, 0) / nucleo.length;
    } else { pu = VALLE[l]; pv = MH / 2; }
    [pu, pv] = enTierra(pu, pv); plazas[l] = [pu, pv];
    const ban = bandera(l), [bu, bv] = enTierra(pu, pv - 1.6); ban.position.set(X(bu), Math.max(suelo(X(bu), Z(bv)), 0), Z(bv)); pueblos.add(ban);
    const ep = estiloDe(e, l);
    for (const o of obras.filter(o => o.lado === l && o.tipo !== 'campo')) {
      const p = pieza(o, ep); let u = o.x + .5 + (hash(o.id, 1) - .5) * .3, v = o.y + .5 + (hash(o.id, 2) - .5) * .3;
      if (o.tipo === 'barco') { p.position.set(X(u), NIVEL + .02, Z(v)); }
      else {
        if (altura(u, v) <= .25) [u, v] = enTierra(u, v);
        const rr = radioDe(o.tipo, ep), libre = (u2, v2) => altura(u2, v2) > .25 && obstaculos.every(b => Math.hypot(X(u2) - b.x, Z(v2) - b.z) > (rr + b.r) * .92);
        if (o.tipo !== 'camino' && !libre(u, v)) busca: for (let r = .5; r < 7; r += .45) for (let k = 0; k < 12; k++) {
          const an = k / 12 * Math.PI * 2 + r, u2 = u + Math.cos(an) * r, v2 = clamp(v + Math.sin(an) * r, 1, MH - 2); if (libre(u2, v2)) { u = u2; v = v2; break busca; } }
        p.position.set(X(u), Math.max(suelo(X(u), Z(v)), 0) - .02, Z(v));
      }
      p.rotation.y = Math.atan2(X(pu) - p.position.x, Z(pv) - p.position.z) + (hash(o.id, 3) - .5) * .5;
      if (o.dueno === 'comun' && o.tipo !== 'casa') { const b = banderita(l); b.position.set(.5, 0, .5); p.add(b); }
      if (o.tipo === 'casa') p.userData.casa = e.agentes.filter(a => a.casa && a.casa[0] === o.x && a.casa[1] === o.y && a.edad >= 14).map(a => a.nombre);
      p.userData.obra = o; pueblos.add(p);
      if (RADIO[o.tipo]) obstaculos.push({ x: p.position.x, z: p.position.z, r: radioDe(o.tipo, ep) });
    }
  }
  pueblos.add(campos(listaCampos, ocupado));
  setTimeout(() => { for (const o of obstaculos) talar(o.x, o.z, o.r + .9); for (const l of 'AB') { const pl = plazas[l]; if (pl) talar(X(pl[0]), Z(pl[1]), 2.4); } }, 0);
}
function animarObras(t, dt) {
  for (const g of GIRAN) g.rotation.z += dt * .8;
  for (const g of FLOTAN) g.position.y = 1.2 + Math.sin(t * .6) * .25;
}

// ---------------- objetos en la mano y ropa ----------------
const PREFIERE = {
  talar: ['hacha', 'sierra', 'piedra afilada', 'cuchillo', 'maza', 'herramienta'],
  picar_piedra: ['pico', 'martillo', 'maza', 'piedra afilada', 'herramienta'], extraer_metal: ['pico', 'martillo', 'herramienta'], extraer_carbon: ['hacha', 'pala', 'herramienta'],
  construir_refugio: ['martillo', 'hacha', 'piedra afilada', 'herramienta'], construir: ['martillo', 'hacha', 'pala', 'piedra afilada', 'herramienta'],
  cultivar: ['azada', 'pala', 'hoz', 'herramienta'], recolectar: ['cesta', 'saco', 'vasija', 'cuenco', 'recipiente', 'hoz'], extraer_arcilla: ['pala', 'vasija', 'cuenco', 'recipiente'],
  cazar: ['arco', 'lanza', 'honda', 'maza', 'arma', 'cuchillo'], pescar: ['lanza', 'arco'], fabricar: ['martillo', 'cuchillo', 'piedra afilada', 'herramienta'],
  descansar: ['flauta', 'tambor', 'instrumento'], leer: ['libro', 'tablilla', 'pergamino', 'escritura'], intercambiar: ['moneda', 'concha', 'balanza']
};
const IZQUIERDA = new Set(['cesta', 'saco', 'vasija', 'cuenco', 'odre', 'jarra', 'recipiente', 'escudo', 'tablilla', 'libro', 'pergamino', 'escritura', 'tambor']);
const MATERIAL = { piedra: '#8E8A80', hueso: '#E6DDC8', madera: '#8A6038', cobre: '#B87333', bronce: '#B08D57', hierro: '#6E7377', metal: '#9AA3A8', oro: '#D4AF37', arcilla: '#B5653A', barro: '#9A6440' };
function objeto3d(o) {
  const g = new THREE.Group(), cab = o.color || MATERIAL[o.material] || '#8C8A86', mango = '#6E4A2C';
  const glb = modeloGLB(o.modelo && o.modelo !== 'nuevo' ? o.modelo : 'objeto:' + o.tipo, .45); if (glb) { glb.rotation.x = Math.PI; g.add(glb); return g; }
  const palo = (len, y = -len / 2) => B(.035, len, .035, mango, 0, y, 0);
  switch (o.tipo) {
    case 'hacha': g.add(palo(.5), B(.16, .11, .03, cab, .07, -.44, 0)); break;
    case 'piedra afilada': g.add(palo(.4), PZ(new THREE.DodecahedronGeometry(.065, 0), cab, .03, -.4, 0), B(.05, .03, .05, '#B9A47A', 0, -.36, 0)); break;
    case 'pico': g.add(palo(.5)); { const h = B(.34, .04, .04, cab, 0, -.48, 0); g.add(h); } break;
    case 'pala': g.add(palo(.55), B(.14, .2, .02, cab, 0, -.64, 0)); break;
    case 'azada': g.add(palo(.55), B(.15, .03, .1, cab, 0, -.56, .05)); break;
    case 'hoz': g.add(palo(.16)); { const r = PZ(new THREE.TorusGeometry(.11, .012, 4, 10, Math.PI * 1.2), cab, .06, -.24, 0); g.add(r); } break;
    case 'martillo': g.add(palo(.34), B(.13, .06, .06, cab, 0, -.34, 0)); break;
    case 'cuchillo': g.add(palo(.09), B(.03, .17, .01, cab, 0, -.18, 0)); break;
    case 'sierra': g.add(palo(.1), B(.05, .34, .01, cab, 0, -.27, 0)); break;
    case 'lanza': g.add(B(.035, 1.25, .035, mango, 0, -.3, 0), PZ(new THREE.ConeGeometry(.04, .14, 5), cab, 0, -.98, 0)); g.children[1].rotation.x = Math.PI; break;
    case 'arco': { const r = PZ(new THREE.TorusGeometry(.32, .015, 4, 12, Math.PI), o.color || mango, 0, -.1, 0); r.rotation.z = Math.PI / 2; g.add(r, B(.005, .64, .005, '#EDEAE2', -.02, -.1, 0)); } break;
    case 'honda': g.add(B(.01, .3, .01, '#B9A47A', 0, -.15, 0), PZ(new THREE.IcosahedronGeometry(.04, 0), o.color || '#9A6B42', 0, -.3, 0)); break;
    case 'maza': g.add(palo(.4), PZ(new THREE.IcosahedronGeometry(.08, 0), cab, 0, -.42, 0)); break;
    case 'escudo': { const e = CIL(.18, .18, .03, o.color || '#9A6B42', 0, -.15, .06, 10); e.rotation.x = Math.PI / 2; g.add(e); } break;
    case 'cesta': g.add(CIL(.12, .09, .14, o.color || '#B9A47A', 0, -.12, 0, 8)); break;
    case 'saco': case 'odre': g.add(PZ(new THREE.IcosahedronGeometry(.1, 0), o.color || '#9A6B42', 0, -.12, 0)); break;
    case 'vasija': case 'jarra': case 'cuenco': g.add(PZ(new THREE.SphereGeometry(.09, 8, 6), o.color || '#B5653A', 0, -.12, 0)); break;
    case 'tambor': g.add(CIL(.1, .1, .14, o.color || '#9A6B42', 0, -.1, .08, 10)); break;
    case 'flauta': g.add(B(.025, .26, .025, o.color || '#E6DDC8', 0, -.13, 0)); break;
    case 'tablilla': case 'libro': case 'pergamino': case 'escritura': g.add(B(.14, .18, .03, o.color || (o.tipo === 'tablilla' ? '#B5653A' : '#D8C7A0'), 0, -.12, .05)); break;
    case 'moneda': case 'concha': g.add(CIL(.04, .04, .01, o.color || '#D4AF37', 0, -.06, 0, 8)); break;
    default: g.add(palo(.4), PZ(new THREE.IcosahedronGeometry(.07, 0), cab, 0, -.4, 0));
  }
  return g;
}
function ponerEn(grupo, o) { while (grupo.children.length) grupo.remove(grupo.children[0]); if (o) grupo.add(objeto3d(o)); }
// Lo que saca para cada tarea: solo si de verdad lo tiene. Sin herramienta, trabaja con las manos.
function sacarObjeto(u, acc) {
  const objs = u.a.objetos || [], pref = PREFIERE[acc] || [];
  let o = null; for (const t of pref) { o = objs.slice().reverse().find(x => x.tipo === t); if (o) break; }
  if (!o && pref.length) { const cat = pref.includes('arco') ? 'arma_caza' : pref.includes('cesta') ? 'recipiente' : pref.includes('flauta') ? 'instrumento' : 'herramienta';
    o = objs.slice().reverse().find(x => x.categoria === cat); }
  const clave = o ? o.tipo + (o.color || '') + glbVersion : '';
  if (!u.manoD) { u.manoD = u.herr; u.manoI = new THREE.Group(); u.manoI.position.set(0, -.33, .02); u.manoI.rotation.x = Math.PI / 2; u.bI.add(u.manoI); }
  const izq = o && IZQUIERDA.has(o.tipo), escudo = objs.find(x => x.tipo === 'escudo');
  if (u.claveMano !== clave) { u.claveMano = clave; ponerEn(u.manoD, izq ? null : o); ponerEn(u.manoI, izq ? o : null); }
  u.manoD.visible = !!o && !izq; u.manoI.visible = !!o && izq;
  if (!u.manoI.visible && escudo && (acc === 'cazar' || acc === 'explorar')) { if (u.claveMano !== 'escudo') { u.claveMano = 'escudo'; ponerEn(u.manoI, escudo); } u.manoI.visible = true; }
  return !!o;
}
// Ropa: cada prenda con el color que eligieron. El cinturón siempre lleva el color de su sociedad.
function vestir(g) {
  const u = g.userData, a = u.a, ropa = (a.objetos || []).filter(o => o.categoria === 'ropa');
  const firma = ropa.map(o => o.tipo + (o.color || '') + (o.material || '')).join('|'); if (u.firmaRopa === firma) return; u.firmaRopa = firma;
  const ultima = ts => ropa.slice().reverse().find(o => ts.includes(o.tipo));
  const col = o => MF(o.color || MATERIAL_ROPA[o.material] || '#9A6B42');
  const arriba = ultima(['tunica', 'camisa', 'camiseta', 'abrigo', 'ropa']) || (ropa.length && !ultima(['capa', 'sombrero', 'gorro', 'falda', 'pantalon', 'botas']) ? ropa[ropa.length - 1] : null);
  const mTorso = arriba ? col(arriba) : MF(COLOR[a.lado]);
  u.torso.material = mTorso; for (const b of [u.bI, u.bD]) b.children[0].material = mTorso;
  const piernas = ultima(['pantalon']), botas = ultima(['botas']);
  for (const p of [u.pI, u.pD]) { if (piernas) p.children[0].material = col(piernas); if (botas) p.children[1].material = col(botas); }
  if (u.extras) u.extras.forEach(x => x.parent && x.parent.remove(x)); u.extras = [];
  const capa = ultima(['capa']); if (capa) { const c = B(.32, .5, .02, capa.color || '#7A5232', 0, .14, -.11); u.torso.add(c); u.extras.push(c); }
  const tun = ultima(['tunica', 'abrigo', 'falda']); if (tun) { const f = B(.33, .2, .2, (tun.color || MATERIAL_ROPA[tun.material] || '#9A6B42'), 0, -.08, 0); u.cad.add(f); u.extras.push(f); }
  const som = ultima(['sombrero', 'gorro']);
  if (som) { const s = new THREE.Group(); s.position.y = .25; if (som.tipo === 'sombrero') s.add(CIL(.22, .22, .02, som.color || '#C8963E', 0, 0, 0, 10), CIL(.11, .12, .12, som.color || '#C8963E', 0, .07, 0, 10));
    else s.add(PZ(new THREE.SphereGeometry(.15, 8, 5, 0, Math.PI * 2, 0, Math.PI / 2), som.color || '#7A5232', 0, -.03, 0)); u.cuello.add(s); u.extras.push(s); }
  u.extras.forEach(x => x.traverse(o => { if (o.isMesh) o.castShadow = true; }));
}
const MATERIAL_ROPA = { piel: '#9A6B42', pieles: '#9A6B42', lino: '#E3D9C2', lana: '#D9CDB8', fibra: '#B9A47A' };

// Como con los árboles: si una construcción tapa a la persona que se sigue, se aparta de la vista.
let obrasOcultas = false;
function despejarObras(p, camPos) {
  if (!p) { if (obrasOcultas) { pueblos.children.forEach(o => o.visible = true); obrasOcultas = false; } return; }
  const lx = camPos.x - p.x, lz = camPos.z - p.z, L2 = lx * lx + lz * lz || 1;
  for (const o of pueblos.children) {
    if (!o.userData.obra) continue;
    const dx = o.position.x - p.x, dz = o.position.z - p.z, t = (dx * lx + dz * lz) / L2, ex = dx - lx * t, ez = dz - lz * t;
    const r = (RADIO[o.userData.obra.tipo] || .5) + .5;
    o.visible = !(t > 0 && t <= 1.05 && ex * ex + ez * ez < r * r && dx * dx + dz * dz > .6);
  }
  obrasOcultas = true;
}
