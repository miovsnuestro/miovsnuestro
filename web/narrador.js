// Mío vs Nuestro · El Narrador: el chat de la pantalla principal.
// No es un habitante: es la voz del experimento. Casi todo lo responde gratis con su banco de preguntas,
// que se actualiza solo con cada día simulado (sim/narrador.py). Solo lo que no sabe pasa por la IA, con límite.
(function () {
  if (typeof REEL !== 'undefined' && REEL) return;
  const css = document.createElement('style');
  css.textContent = `
  #bnarrador{position:absolute;left:10px;bottom:84px;pointer-events:auto;background:#FAC775;color:#1b1b1b;border:0;border-radius:22px;
    padding:9px 14px;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 2px 12px rgba(0,0,0,.25);display:flex;align-items:center;gap:6px}
  #bnarrador .pulso{width:8px;height:8px;border-radius:50%;background:#1D9E75;box-shadow:0 0 0 0 rgba(29,158,117,.6);animation:npulso 2s infinite}
  @keyframes npulso{0%{box-shadow:0 0 0 0 rgba(29,158,117,.6)}70%{box-shadow:0 0 0 9px rgba(29,158,117,0)}100%{box-shadow:0 0 0 0 rgba(29,158,117,0)}}
  #narrador{left:10px;right:10px;bottom:74px;display:flex;flex-direction:column;max-width:520px;padding:10px 12px;gap:8px}
  #narrador .nh{display:flex;align-items:center;gap:8px}#narrador .nh b{font-size:15px}#narrador .nh span{font-size:11px;opacity:.7;flex:1}
  #narrador .nh button{background:rgba(255,255,255,.12);color:#fff;border:0;border-radius:8px;width:30px;height:28px;cursor:pointer;font-size:14px}
  #nmsgs{flex:1 1 auto;min-height:40px;overflow-y:auto;-webkit-overflow-scrolling:touch;display:flex;flex-direction:column;gap:7px;user-select:text;-webkit-user-select:text}
  .nm{max-width:88%;padding:8px 11px;border-radius:14px;font-size:13.5px;line-height:1.45}
  .nm.yo{align-self:flex-end;background:#FAC775;color:#1b1b1b;border-bottom-right-radius:4px}
  .nm.el{align-self:flex-start;background:rgba(255,255,255,.1);border-bottom-left-radius:4px}
  .nm.el .soc.sB{color:#FF9B7A}.nm.el .soc.sA{color:#4FE0B0}
  .nm .via{display:block;font-size:10px;opacity:.55;margin-top:4px}
  .nm .segs{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}.nm .seg{background:rgba(255,255,255,.14);border:0;color:#fff;border-radius:9px;padding:5px 9px;font-size:12px;cursor:pointer}
  .nm.escribe{opacity:.7;font-style:italic}
  #nsug,#nform,#narrador .nh,#narrador .nnota{flex:none}
  #nsug{display:flex;gap:6px;overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:2px;scrollbar-width:none}#nsug::-webkit-scrollbar{display:none}
  #nsug button{flex:none;background:rgba(250,199,117,.14);color:#FAC775;border:1px solid rgba(250,199,117,.45);border-radius:14px;padding:6px 10px;font-size:12px;cursor:pointer;white-space:nowrap}
  #nform{display:flex;gap:6px}#nform input{flex:1;min-width:0;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);color:#fff;border-radius:10px;padding:9px 10px;font-size:15px;outline:none}
  #nform button{background:#FAC775;color:#1b1b1b;font-weight:650;border:0;border-radius:10px;padding:8px 12px;cursor:pointer}
  #narrador .nnota{font-size:10.5px;opacity:.6}
  body.con-ficha #bnarrador,body.con-narrador #bnarrador,body.con-narrador #ficha,body.con-narrador #ia{display:none!important}
  @media (min-width:900px){#narrador{left:10px;right:auto;width:440px}}
  @media (max-width:700px) and (orientation:portrait){#bnarrador{padding:8px 12px;font-size:12.5px}body.con-narrador #botones{display:none}}
  @media (max-height:500px) and (orientation:landscape){
    #bnarrador{left:auto;right:8px;bottom:auto;top:50%;transform:translateY(-50%);padding:6px 10px;font-size:11.5px}
    #bnarrador span.t{display:none}
    #narrador{left:auto;right:8px;bottom:6px;width:46%;max-width:none;padding:7px 10px;gap:5px;background:rgba(14,20,24,.82)}
    .nm{font-size:12px;padding:6px 9px}body.con-narrador #botones{display:none}
  }`;
  document.head.appendChild(css);

  const b = document.createElement('button');
  b.id = 'bnarrador'; b.innerHTML = '<i class="pulso"></i>💬 <span class="t">Pregunta al Narrador</span>';
  b.title = 'Pregúntale lo que quieras sobre el experimento';
  document.body.appendChild(b);
  const p = document.createElement('div');
  p.id = 'narrador'; p.className = 'panel oculto';
  p.innerHTML = '<div class="nh"><b>💬 El Narrador</b><span>la voz del experimento · datos del día</span><button id="ncerrar" title="Cerrar">✕</button></div>' +
    '<div id="nmsgs"></div><div id="nsug"></div>' +
    '<form id="nform" autocomplete="off"><input id="npreg" maxlength="200" placeholder="Pregúntame lo que quieras…" enterkeyhint="send"><button>Enviar</button></form>' +
    '<div class="nnota">Preguntar no cambia nada en el experimento.</div>';
  document.body.appendChild(p);
  const $n = id => document.getElementById(id), msgs = $n('nmsgs');
  let iniciado = false, ocupado = false;

  function colocar() {
    if (p.classList.contains('oculto')) return;
    const cr = $n('cronica').getBoundingClientRect(), mk = $n('marcador').getBoundingClientRect();
    if (innerHeight <= 500 && innerWidth > innerHeight) { p.style.bottom = '6px'; p.style.maxHeight = (innerHeight - mk.bottom - 14) + 'px'; }
    else { p.style.bottom = (innerHeight - cr.top + 8) + 'px'; p.style.maxHeight = Math.max(200, cr.top - mk.bottom - 16) + 'px'; }
  }
  function colocarBoton() {
    if (innerHeight <= 500 && innerWidth > innerHeight) { b.style.bottom = ''; return; }
    const cr = $n('cronica').getBoundingClientRect(); b.style.bottom = (innerHeight - cr.top + 8) + 'px';
    const ia = $n('ia'); if (ia) ia.style.bottom = (innerHeight - cr.top + 52) + 'px';
  }
  if (typeof recolocar === 'function') { const antes = recolocar; recolocar = function () { antes(); colocarBoton(); colocar(); }; }
  addEventListener('resize', () => setTimeout(() => { colocarBoton(); colocar(); }, 80));
  setTimeout(colocarBoton, 300);

  function mensaje(texto, quien, extra) {
    const d = document.createElement('div'); d.className = 'nm ' + quien;
    if (quien === 'yo') d.textContent = texto; else d.innerHTML = (typeof colorear === 'function' ? colorear(texto) : texto);
    if (extra && extra.via === 'ia') { const v = document.createElement('span'); v.className = 'via'; v.textContent = 'Respuesta generada con IA'; d.appendChild(v); }
    const per = (extra && extra.personas) || [];
    if (per.length) {
      const fila = document.createElement('div'); fila.className = 'segs'; d.appendChild(fila);
      for (const x of per) {
        const s = document.createElement('button'); s.className = 'seg'; s.textContent = '👁 Seguir a ' + x.nombre;
        s.onclick = () => { const g = typeof gente !== 'undefined' && gente.get(x.id); if (g) { cerrar(); seguir(g); } };
        fila.appendChild(s);
      }
    }
    msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight; return d;
  }
  function chips(lista) {
    const s = $n('nsug'); s.innerHTML = '';
    for (const t of lista || []) { const c = document.createElement('button'); c.type = 'button'; c.textContent = t; c.onclick = () => enviar(t); s.appendChild(c); }
  }
  async function abrir() {
    p.classList.remove('oculto'); document.body.classList.add('con-narrador'); colocar();
    if (!iniciado) {
      iniciado = true;
      try { const d = await (await fetch('/api/narrador/inicio')).json(); mensaje(d.saludo, 'el'); chips(d.sugerencias); }
      catch (e) { mensaje('¡Hola! Soy el Narrador. Pregúntame qué ha pasado hoy, quién es quién o cómo funciona el experimento.', 'el');
        chips(['¿Qué ha pasado hoy?', '¿Quién va ganando?', '¿Cómo funciona?']); }
    }
    if (!('ontouchstart' in window)) setTimeout(() => $n('npreg').focus(), 60);
  }
  function cerrar() { p.classList.add('oculto'); document.body.classList.remove('con-narrador'); if (typeof recolocar === 'function') recolocar(); }
  async function enviar(t) {
    t = (t || '').trim(); if (!t || ocupado) return; ocupado = true;
    mensaje(t, 'yo'); $n('npreg').value = ''; const esp = mensaje('Mirando lo que ha pasado…', 'el escribe');
    try {
      const r = await fetch('/api/narrador/preguntar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pregunta: t }) });
      const d = await r.json(); esp.remove(); mensaje(d.respuesta || 'Ahora mismo no puedo contestar.', 'el', d); chips(d.sugerencias);
    } catch (e) { esp.remove(); mensaje('No hay conexión con el mundo ahora mismo. Prueba en un momento.', 'el'); }
    ocupado = false;
  }
  b.onclick = abrir; $n('ncerrar').onclick = cerrar;
  $n('nform').onsubmit = e => { e.preventDefault(); enviar($n('npreg').value); };
  for (const ev of ['pointerdown', 'wheel', 'touchstart', 'keydown']) p.addEventListener(ev, e => e.stopPropagation(), { passive: true });
  window.abrirNarrador = abrir;
})();
