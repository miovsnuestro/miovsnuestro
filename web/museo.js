// ---------------- Casa de los inventos ----------------
// Cada sociedad tiene la suya junto a su plaza: el mismo edificio para las dos (solo cambia el color), que cambia con la época.
// Al tocarla se abre una vitrina con todos sus inventos en 3D, uno a uno, con una breve descripción.
const MUSEOS = {};
function cartel(txt, tam = 128) {  // un icono flotante para que se vea desde lejos que ahí se puede entrar
  const c = document.createElement('canvas'); c.width = c.height = tam; const x = c.getContext('2d');
  x.fillStyle = 'rgba(20,26,30,.82)'; x.beginPath(); x.arc(tam / 2, tam / 2, tam / 2 - 4, 0, Math.PI * 2); x.fill();
  x.lineWidth = 6; x.strokeStyle = '#FAC775'; x.stroke();
  x.font = Math.round(tam * .5) + 'px sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(txt, tam / 2, tam / 2 + 4);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false, transparent: true }));
  s.renderOrder = 10; return s;
}
function casaDeInventos(ep, lado) {
  const g = new THREE.Group(), acento = lado === 'A' ? '#2F8A6A' : '#C8613A';
  if (ep === 'prehistoria') {  // una choza grande de pieles, con piedras alrededor y un poste tallado delante
    g.add(PZ(new THREE.ConeGeometry(1.25, 2.2, 10), '#C9A06A', 0, 1.1, 0), CIL(.86, .98, .16, acento, 0, .78, 0, 10));
    for (let i = 0; i < 5; i++) { const p = CIL(.03, .03, .7, '#5A3A20', Math.cos(i * 1.26) * .12, 2.35, Math.sin(i * 1.26) * .12, 4); p.rotation.set(Math.sin(i * 1.26) * .4, 0, -Math.cos(i * 1.26) * .4); g.add(p); }
    const puerta = B(.55, .8, .05, '#3A2616', 0, .4, 1.02); puerta.rotation.x = -.45; g.add(puerta);
    for (let i = 0; i < 12; i++) g.add(PZ(new THREE.DodecahedronGeometry(.12, 0), '#8A857C', Math.cos(i * .52) * 1.45, .06, Math.sin(i * .52) * 1.45));
    g.add(CIL(.07, .09, 1.5, '#6E4A2C', .95, .75, 1.15, 6), B(.22, .16, .16, acento, .95, 1.35, 1.15), PZ(new THREE.IcosahedronGeometry(.11, 0), '#E8C26A', .95, 1.56, 1.15));
  } else if (ep === 'aldeas') {  // una casa larga de madera con tejado a dos aguas y estandarte
    g.add(B(2.6, 1.1, 1.6, '#B48A5A', 0, .55, 0));
    const t = PZ(new THREE.CylinderGeometry(.01, 1.15, 2.8, 3), '#CDB35C', 0, 1.45, 0); t.rotation.z = Math.PI / 2; t.rotation.x = Math.PI / 2; t.scale.set(1, 1, .75); g.add(t);
    g.add(B(.5, .75, .05, '#4A2E1E', 0, .38, .81), B(2.7, .1, .1, acento, 0, 1.1, .82), CIL(.04, .04, 2.6, '#6E4A2C', 1.5, 1.3, .9, 5), B(.5, .32, .02, acento, 1.76, 2.3, .9));
  } else if (ep === 'metal') {  // de piedra, con columnas y frontón
    g.add(B(2.6, .2, 1.8, '#9A958A', 0, .1, 0), B(2.2, 1.2, 1.3, '#C9C2B2', 0, .8, -.1));
    for (const x of [-1, -.35, .35, 1]) g.add(CIL(.1, .12, 1.25, '#DDD6C6', x, .82, .72, 8));
    const fr = PZ(new THREE.CylinderGeometry(.01, .8, 2.5, 3), '#B9B2A2', 0, 1.62, .25); fr.rotation.z = Math.PI / 2; fr.rotation.x = Math.PI / 2; fr.scale.set(1, 1, .45); g.add(fr);
    g.add(B(2.5, .08, 1.6, acento, 0, 1.47, .2), B(.5, .8, .05, '#4A3A2A', 0, .6, .56));
  } else {  // industrial, moderna y espacial: una sala con mucho cristal
    const cristal = ep === 'industrial' ? '#6E8796' : '#8FB8CC';
    g.add(B(2.8, .15, 1.9, '#9A958A', 0, .075, 0), B(2.5, 1.5, 1.6, ep === 'industrial' ? '#A0563B' : '#ECEAE4', 0, .9, 0));
    g.add(B(2.1, 1.05, .04, cristal, 0, .85, .82), B(2.6, .14, 1.7, acento, 0, 1.72, 0));
    if (ep === 'espacial') g.add(PZ(new THREE.SphereGeometry(.6, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), '#CFD6DC', 0, 1.79, 0));
  }
  const s = cartel('💡'); s.scale.set(.9, .9, 1); s.position.y = ep === 'prehistoria' ? 3.2 : 2.9; g.add(s); g.userData.cartel = s;
  sombra(g); s.castShadow = false; return g;
}
// Fuera del mapa en el que viven: en la ladera norte, por encima de su valle. Los habitantes no la ven, no la pisan y el motor
// no sabe que existe; es solo para quien visita la web. Se sienta sobre una terraza de piedra para quedar plana en la ladera.
function ponerMuseo(e, l, ep) {
  delete MUSEOS[l]; const g = casaDeInventos(ep, l), base = VALLE[l]; let mejor = null;
  for (let du = -12; du <= 12; du += 1) for (let v = -2.5; v >= -5; v -= .5) {
    const u = clamp(base + du, 3, MW - 3), hs = [[0, 0], [1.6, 0], [-1.6, 0], [0, 1.4], [0, -1.4]].map(([a, b]) => altura(u + a, v + b));
    const pend = Math.max(...hs) - Math.min(...hs), nota = pend + Math.abs(du) * .02 + Math.max(0, Math.max(...hs) - 2.5);
    if (Math.min(...hs) > .3 && (!mejor || nota < mejor.nota)) mejor = { u, v, nota, alto: Math.max(...hs), bajo: Math.min(...hs) };
  }
  if (!mejor) return;
  const terr = B(3.1, mejor.alto - mejor.bajo + .3 , 2.9, '#8A7A5E', 0, -(mejor.alto - mejor.bajo + .3) / 2 + .05, 0); terr.receiveShadow = true; g.add(terr);
  g.position.set(X(mejor.u), mejor.alto, Z(mejor.v));
  g.rotation.y = Math.atan2(X(VALLE[l]) - g.position.x, Z(MH / 2) - g.position.z) * .35;  // mira hacia su valle
  g.userData.museo = l; pueblos.add(g); MUSEOS[l] = g;
  obstaculos.push({ x: g.position.x, z: g.position.z, r: 1.9 });
}
function animarMuseos(t) { for (const l in MUSEOS) { const s = MUSEOS[l].userData.cartel; if (s) { s.userData.y0 ??= s.position.y; s.position.y = s.userData.y0 + Math.sin(t * 2 + (l === 'A' ? 1 : 0)) * .12; } } }

// ---------------- la vitrina ----------------
let vit = null;  // {R, S, C, pieza, lado, i, lista, yaw, pitch, arrastre}
function vitrinaHTML() {
  const d = document.createElement('div'); d.id = 'vitrina'; d.className = 'panel oculto';
  d.innerHTML = '<div class="ch"><div class="pes"><button data-vit="B">Los del Nuestro</button><button data-vit="A">Los del Mío</button></div><button id="vcerrar" title="Cerrar">✕</button></div>'
    + '<div id="vtit">🏛️ Casa de los inventos</div>'
    + '<div id="vescena"><canvas id="vlienzo"></canvas><button id="vant" title="Anterior">‹</button><button id="vsig" title="Siguiente">›</button><div id="vpos"></div><div id="vgira">Arrastra para girarlo</div></div>'
    + '<div id="vinfo"></div><div id="vtira"></div>'
    + '<div class="chnota">Cada invento lo crearon ellos. Su forma 3D es una representación; la descripción y para qué sirve los fija el árbitro, con las mismas reglas para los dos lados. Contenido generado con IA.</div>';
  document.body.appendChild(d);
  const st = document.createElement('style');
  st.textContent = `#vitrina{left:10px;right:10px;top:60px;max-height:calc(100vh - 140px);overflow-y:auto;z-index:7;display:flex;flex-direction:column;padding:8px 10px;max-width:560px;margin:0 auto}
  #vitrina.oculto{display:none}#vitrina .ch{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px}
  #vitrina .pes{display:flex;gap:4px}#vitrina .pes button{border:1.5px solid transparent;border-radius:9px;padding:4px 9px;background:rgba(255,255,255,.1);color:#fff;font:inherit;font-size:12px;font-weight:650;cursor:pointer;opacity:.6}
  #vitrina .pes button[data-vit=B].on{border-color:var(--B);background:rgba(216,90,48,.3);opacity:1}#vitrina .pes button[data-vit=A].on{border-color:var(--A);background:rgba(29,158,117,.3);opacity:1}
  #vcerrar{border:0;background:none;color:#fff;font-size:16px;cursor:pointer;padding:2px 6px}
  #vtit{font-size:11px;opacity:.7;margin:0 2px 4px}
  #vescena{position:relative;flex:0 0 auto;height:42vh;min-height:170px;border-radius:12px;overflow:hidden;background:radial-gradient(ellipse at 50% 40%,#3B4A52 0%,#1A2226 75%);touch-action:none}
  #vlienzo{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:grab}
  #vant,#vsig{position:absolute;top:50%;transform:translateY(-50%);width:38px;height:38px;border-radius:50%;border:0;background:rgba(0,0,0,.45);color:#fff;font-size:24px;line-height:1;cursor:pointer}
  #vant{left:8px}#vsig{right:8px}#vant:disabled,#vsig:disabled{opacity:.25;cursor:default}
  #vpos{position:absolute;top:8px;left:10px;font-size:11px;opacity:.75}#vgira{position:absolute;bottom:7px;left:0;right:0;text-align:center;font-size:10.5px;opacity:.55;pointer-events:none}
  #vinfo{padding:8px 2px 4px;font-size:12.5px;line-height:1.45}#vinfo .nm{font-size:16px;font-weight:700}#vinfo .tg{display:inline-block;font-size:9.5px;padding:0 5px;border-radius:6px;background:rgba(255,255,255,.12);margin-left:6px;vertical-align:2px;font-weight:600}
  #vinfo .ds{font-style:italic;opacity:.92;margin:3px 0}#vinfo .q{font-size:11px;opacity:.65}
  #vtira{display:flex;gap:5px;overflow-x:auto;padding:4px 1px 6px;-webkit-overflow-scrolling:touch;flex:0 0 auto}
  #vtira button{flex:0 0 34px;height:34px;border-radius:9px;border:1.5px solid transparent;background:rgba(255,255,255,.1);font-size:17px;cursor:pointer;padding:0}
  #vtira button.on{border-color:#FAC775;background:rgba(250,199,117,.22)}
  @media (min-width:900px){#vitrina{left:auto;right:10px;width:540px;top:215px;max-height:calc(100vh - 300px)}#vescena{height:min(42vh,340px)}}
  @media (max-height:520px){#vitrina{top:6px;max-height:calc(100vh - 12px)}}`;
  document.head.appendChild(st);
  for (const ev of ['pointerdown', 'wheel']) d.addEventListener(ev, x => x.stopPropagation(), { passive: true });
  d.querySelectorAll('[data-vit]').forEach(b => b.onclick = x => { x.stopPropagation(); abrirVitrina(b.dataset.vit); });
  d.querySelector('#vcerrar').onclick = cerrarVitrina;
  d.querySelector('#vant').onclick = () => irInvento(vit.i - 1); d.querySelector('#vsig').onclick = () => irInvento(vit.i + 1);
  addEventListener('keydown', x => { if (!vit || !vit.abierta) return; if (x.key === 'ArrowLeft') irInvento(vit.i - 1); if (x.key === 'ArrowRight') irInvento(vit.i + 1); if (x.key === 'Escape') cerrarVitrina(); });
  const cv = d.querySelector('#vlienzo'), ps = new Map(); let toque0 = null;
  cv.addEventListener('pointerdown', x => { cv.setPointerCapture(x.pointerId); ps.set(x.pointerId, x.clientX); toque0 = { x: x.clientX, y: x.clientY, t: performance.now() }; vit.quieto = 0; });
  cv.addEventListener('pointermove', x => { if (!ps.has(x.pointerId)) return; const dx = x.clientX - ps.get(x.pointerId); ps.set(x.pointerId, x.clientX); vit.yaw += dx * .012; vit.quieto = 0; });
  const fin = x => { ps.delete(x.pointerId);  // un deslizamiento rápido pasa al siguiente o al anterior
    if (toque0 && performance.now() - toque0.t < 260 && Math.abs(x.clientX - toque0.x) > 60) irInvento(vit.i + (x.clientX < toque0.x ? 1 : -1)); toque0 = null; };
  cv.addEventListener('pointerup', fin); cv.addEventListener('pointercancel', fin);
  cv.addEventListener('wheel', x => { x.preventDefault(); vit.dist = clamp(vit.dist * Math.exp(x.deltaY * .001), .6, 1.8); }, { passive: false });
}
function iniciarVitrina() {
  if (vit) return; vitrinaHTML();
  const cv = $('vlienzo'), R2 = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true });
  R2.setPixelRatio(Math.min(devicePixelRatio, 2)); R2.shadowMap.enabled = false;
  const S2 = new THREE.Scene(), C2 = new THREE.PerspectiveCamera(35, 1, .05, 100);
  S2.add(new THREE.HemisphereLight('#FFF6E6', '#3A4448', .62));
  const sol = new THREE.DirectionalLight('#FFFFFF', .62); sol.position.set(2, 4, 3); S2.add(sol);
  const peana = new THREE.Mesh(new THREE.CylinderGeometry(1, 1.08, .12, 32), new THREE.MeshPhongMaterial({ color: '#59666D', shininess: 10 })); peana.position.y = -.06; S2.add(peana);
  const soporte = new THREE.Group(); S2.add(soporte);
  vit = { R: R2, S: S2, C: C2, soporte, peana, lado: 'B', i: 0, lista: [], yaw: .6, dist: 1, quieto: 0, abierta: false, t0: performance.now() };
  addEventListener('resize', ajustarVitrina);
  requestAnimationFrame(pintarVitrina);
}
function ajustarVitrina() { if (!vit) return; const c = $('vescena').getBoundingClientRect(); if (!c.width) return; vit.R.setSize(c.width, c.height, false); vit.C.aspect = c.width / c.height; vit.C.updateProjectionMatrix(); }
// Solo entra en la casa lo que se ve bien: lo que ya tiene su modelo 3D subido, o lo que la web ya sabe dibujar por sí misma.
// Lo que necesitaría un modelo y de momento solo tendría la pieza genérica, espera fuera hasta que se suba su modelo.
const DIBUJA_ESTR = new Set(['casa', 'hoguera', 'corral', 'taller', 'carro', 'barco', 'almacen', 'granero', 'escuela', 'mercado', 'molino', 'torre',
  'observatorio', 'fabrica', 'camino', 'puente', 'maquina', 'globo', 'cohete', 'enfermeria', 'monumento', 'horno', 'pozo', 'muralla']);
const DIBUJA_OBJ = new Set(['hacha', 'piedra afilada', 'pico', 'pala', 'azada', 'hoz', 'martillo', 'cuchillo', 'sierra', 'lanza', 'arco', 'honda', 'maza',
  'escudo', 'cesta', 'saco', 'odre', 'vasija', 'jarra', 'cuenco', 'tambor', 'flauta', 'tablilla', 'libro', 'pergamino', 'escritura', 'moneda', 'concha', 'ropa']);
const SIN_FORMA = new Set(['tecnica', 'oficio', 'organizacion', 'costumbre', 'norma_o_costumbre', 'sistema']);
function seVeBien(i, l) {
  const m = i.modelo || '';
  if (SIN_FORMA.has(i.tipo)) return true;  // una técnica, un oficio, una costumbre: no es una cosa, se enseña como idea
  if (m && (GLB[m] || GLB[m + '@' + estiloDe(est, l)])) return true;  // modelo 3D subido
  if (!m) return false;
  if (m.startsWith('estructura:')) return DIBUJA_ESTR.has(m.slice(11).split('@')[0]) && !i.inedito;
  if (m.startsWith('objeto:')) return DIBUJA_OBJ.has(m.slice(7)) && !i.inedito;
  return false;
}
function listaInventos(l) {
  return ((est && est.sociedades[l].inventos) || []).filter(i => seVeBien(i, l)).map((i, k) => ({ ...i, k })).sort((a, b) => (a.dia || 0) - (b.dia || 0) || a.k - b.k);  // del primero al último: su historia en orden
}
// Su forma: la pieza de construcción, el objeto, o (técnicas, oficios, costumbres…) una idea sobre un atril.
function modeloDeInvento(i, l) {
  const m = SIN_FORMA.has(i.tipo) ? '' : (i.modelo || ''), ep = estiloDe(est, l);
  if (m.startsWith('estructura:')) { const t = m.slice(11).split('@')[0]; return pieza({ tipo: t, lado: l, modelo: m, categoria: i.categoria, id: 0 }, ep); }
  if (i.categoria === 'ropa' || m === 'objeto:ropa') {  // una prenda en su maniquí de palos
    const g = new THREE.Group(), c = '#9A6B42';
    g.add(CIL(.03, .03, 1, '#6E4A2C', 0, .5, 0, 4), B(.5, .04, .04, '#6E4A2C', 0, .95, 0));
    g.add(PZ(new THREE.CylinderGeometry(.2, .3, .62, 8), c, 0, .62, 0), B(.56, .14, .2, c, 0, .9, 0), B(.12, .3, .14, c, -.3, .76, 0), B(.12, .3, .14, c, .3, .76, 0));
    g.add(PZ(new THREE.TorusGeometry(.25, .025, 4, 16), COLOR[l], 0, .52, 0)); g.children[g.children.length - 1].rotation.x = Math.PI / 2; return g;
  }
  if (m.startsWith('objeto:')) { const g = objeto3d({ tipo: m.slice(7), modelo: m }); g.rotation.z = Math.PI; return g; }  // en la mano cuelga hacia abajo: aquí, de pie
  const g = new THREE.Group();
  g.add(CIL(.05, .07, .6, '#6E4A2C', 0, .3, 0, 6), B(.5, .34, .04, '#D8C7A0', 0, .72, .03));
  const s = cartel(ICONO_CAT[i.categoria] || '💡', 128); s.material.depthTest = true; s.scale.set(.42, .42, 1); s.position.set(0, .72, .08); g.add(s);
  const halo = new THREE.Mesh(new THREE.TorusGeometry(.36, .015, 6, 32), new THREE.MeshBasicMaterial({ color: COLOR[l] })); halo.position.set(0, .72, 0); g.add(halo);
  return g;
}
function encajar(g) {  // a una caja de 1×1, sobre la peana
  g.updateMatrixWorld(true); const caja = new THREE.Box3().setFromObject(g); if (caja.isEmpty()) return g;
  const t = caja.getSize(new THREE.Vector3()), k = 1.25 / Math.max(t.x, t.y * .85, t.z, .001), c = caja.getCenter(new THREE.Vector3());
  const h = new THREE.Group(); g.position.sub(new THREE.Vector3(c.x, caja.min.y, c.z)); h.add(g); h.scale.setScalar(k); return h;
}
function irInvento(n) {
  if (!vit || !vit.lista.length) return; vit.i = clamp(n, 0, vit.lista.length - 1);
  const i = vit.lista[vit.i], l = vit.lado;
  while (vit.soporte.children.length) vit.soporte.remove(vit.soporte.children[0]);
  vit.soporte.add(encajar(modeloDeInvento(i, l))); vit.esperaGLB = (i.modelo && GLB[i.modelo + '@' + estiloDe(est, l)] || GLB[i.modelo]) && !glbListo[i.modelo] ? i.modelo : null;
  vit.yaw = .6; vit.dist = 1; vit.quieto = 0;
  vit.peana.material.color.set(l === 'A' ? '#3E6B5E' : '#6B4E43');
  $('vpos').textContent = (vit.i + 1) + ' / ' + vit.lista.length;
  $('vant').disabled = vit.i === 0; $('vsig').disabled = vit.i === vit.lista.length - 1;
  const pq = paraQue(i.efectos), may = t => String(t || '').replace(/^./, c => c.toUpperCase());
  $('vinfo').innerHTML = '<div><span class="nm">' + (ICONO_CAT[i.categoria] || '💡') + ' ' + colorear(may(i.nombre)) + '</span>' + (TIPO_TXT[i.tipo] ? '<span class="tg">' + TIPO_TXT[i.tipo] + '</span>' : '') + '</div>'
    + (i.descripcion && i.descripcion.trim().toLowerCase() !== String(i.nombre).toLowerCase() ? '<div class="ds">' + colorear(may(i.descripcion)) + '</div>' : '')
    + (pq ? '<div>⚙️ ' + colorear(pq) + '</div>' : '')
    + '<div class="q">' + (i.origen ? 'Aprendido de ' + colorear(i.origen) : i.inventor ? 'Lo inventó ' + colorear(i.inventor) : 'Invento') + (i.dia != null ? ' el día ' + i.dia : '') + ' · el ' + (vit.i + 1) + '.º de ' + colorear(est.sociedades[l].nombre) + '</div>';
  const tira = $('vtira'); tira.querySelectorAll('button').forEach((b, k) => b.classList.toggle('on', k === vit.i));
  const b = tira.children[vit.i]; if (b) b.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
}
function abrirVitrina(l, nombre) {
  if (!est) return; iniciarVitrina(); vit.lado = l; vit.lista = listaInventos(l); vit.abierta = true;
  $('vitrina').classList.remove('oculto'); if (typeof chatLado !== 'undefined' && chatLado) { chatLado = null; $('charla').classList.add('oculto'); }
  document.querySelectorAll('#vitrina [data-vit]').forEach(b => b.classList.toggle('on', b.dataset.vit === l));
  $('vtit').textContent = '🏛️ Casa de los inventos de ' + est.sociedades[l].nombre + ' · ' + vit.lista.length + ' inventos';
  const fuera = ((est.sociedades[l].inventos) || []).length - vit.lista.length;
  if (fuera > 0) $('vtit').textContent += ' · ' + fuera + ' más esperan su modelo 3D';
  $('vtira').innerHTML = vit.lista.map((i, k) => '<button title="' + colorear(i.nombre) + '" data-k="' + k + '">' + (ICONO_CAT[i.categoria] || '💡') + '</button>').join('');
  $('vtira').querySelectorAll('button').forEach(b => b.onclick = () => irInvento(+b.dataset.k));
  ajustarVitrina();
  if (!vit.lista.length) { while (vit.soporte.children.length) vit.soporte.remove(vit.soporte.children[0]); $('vinfo').innerHTML = '<div class="q">Todavía no han inventado nada. La casa está vacía, de momento.</div>'; $('vpos').textContent = ''; $('vant').disabled = $('vsig').disabled = true; return; }
  const k = nombre ? vit.lista.findIndex(i => i.nombre === nombre) : vit.lista.length - 1;  // se abre en lo último que han inventado
  irInvento(k < 0 ? vit.lista.length - 1 : k);
}
function cerrarVitrina() { if (!vit) return; vit.abierta = false; $('vitrina').classList.add('oculto'); }
function pintarVitrina() {
  requestAnimationFrame(pintarVitrina);
  if (!vit || !vit.abierta) return;
  const t = performance.now() / 1000, dt = Math.min(.1, t - (vit.tp || t)); vit.tp = t; vit.quieto += dt;
  if (vit.esperaGLB && glbListo[vit.esperaGLB]) { vit.esperaGLB = null; irInvento(vit.i); }  // llegó su modelo 3D: se cambia la pieza
  if (vit.quieto > 1.2) vit.yaw += dt * .45;  // gira sola mientras nadie la toca
  vit.soporte.rotation.y = vit.yaw;
  const d = 3.3 * vit.dist * Math.max(1, 1.1 / vit.C.aspect); vit.C.position.set(0, .95 + d * .28, d); vit.C.lookAt(0, .55, 0);
  vit.R.render(vit.S, vit.C);
}
