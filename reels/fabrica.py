"""Fábrica de reels: guion → voz → grabación del mundo 3D → montaje → Telegram para aprobar.

Uso (lo lanza cron en el servidor):
    python -m reels.fabrica diario          # reel corto del día (≈30 s)
    python -m reels.fabrica episodio        # episodio de más de 1 minuto (para TikTok/YouTube)
    python -m reels.fabrica rehacer         # vuelve a montar los reels a los que pediste cambios
    python -m reels.fabrica prueba          # monta un reel y lo deja en reels/salida sin enviarlo

Cómo se graba: la web tiene un modo reel en el que el tiempo lo pone este programa. Por cada fotograma
avanza exactamente 1/25 s y saca una captura, así el vídeo sale fluido aunque el servidor no tenga
tarjeta gráfica (antes se grababa «en vivo» y salían pantallas congeladas).

Todo es igual para las dos sociedades: mismo número de escenas, mismo tiempo en pantalla y mismo tono.
Cada reel lleva la etiqueta «Contenido generado con IA».
"""
import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.parse
import wave
from pathlib import Path
from sim import config
from sim.cerebro import llamar_llm
from sim import moderacion

SALIDA = config.RAIZ / "reels" / "salida"
MUSICA = config.RAIZ / "reels" / "musica"
URL_WEB = os.getenv("REEL_URL", "http://127.0.0.1/")
FUENTE = os.getenv("REEL_FUENTE", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
VOZ_PIPER = os.getenv("VOZ_PIPER", str(config.RAIZ / "voces" / "es_ES-davefx-medium.onnx"))
ANCHO, ALTO = 1080, 1920                      # tamaño final del vídeo
RENDER = (int(os.getenv("REEL_RENDER_ANCHO", "720")), int(os.getenv("REEL_RENDER_ALTO", "1280")))  # se dibuja así y se escala
FPS = int(os.getenv("REEL_FPS", "25"))
COLOR = {"A": "0x1D9E75", "B": "0xD85A30", "C": "0xFAC775"}
VERBO = {"recolectar": "recoge comida", "talar": "tala madera", "picar_piedra": "pica piedra", "pescar": "pesca",
         "cazar": "sale a cazar", "cultivar": "cultiva la tierra", "criar": "cuida a los animales", "descansar": "descansa",
         "construir_refugio": "construye una casa", "explorar": "explora", "asentarse": "reclama tierra nueva",
         "inventar": "intenta inventar algo", "hablar": "habla con los suyos", "intercambiar": "hace un trueque",
         "regalar": "regala lo que le sobra", "enseñar": "enseña lo que sabe", "depositar": "guarda en el almacén común",
         "tomar": "coge del almacén común", "cortejar": "busca pareja", "comer": "come", "extraer_arcilla": "saca arcilla",
         "extraer_metal": "busca metal", "extraer_carbon": "saca carbón"}


def mundo_actual():
    return (config.RAIZ / ".mundo").read_text().strip() if (config.RAIZ / ".mundo").exists() else "pruebas"


def bd_reels():
    import bot
    return bot.bd_reels()


def estado_web():
    try:
        return json.loads((config.WEB / "estado.json").read_text())
    except Exception:
        return None


# ---------- 1. guion ----------
def hechos(mundo, dias):
    """Sucesos recientes por sociedad, sin repetir frases y variando el tipo (no cinco cacerías seguidas)."""
    bd = sqlite3.connect(config.DATOS / f"{mundo}.db")
    ultimo = bd.execute("SELECT MAX(dia) FROM sucesos WHERE mundo=?", (mundo,)).fetchone()[0] or 0
    res = {}
    for lado in "AB":
        filas = bd.execute("SELECT dia, agente, tipo, texto, importancia FROM sucesos WHERE mundo=? AND lado=? AND dia>? "
                           "AND importancia>=3 ORDER BY importancia DESC, dia DESC LIMIT 60", (mundo, lado, ultimo - dias)).fetchall()
        vistos, por_tipo = set(), {}
        for d, a, t, x, i in filas:
            texto = moderacion.revisar(x)[0]
            if not texto or texto in vistos:
                continue
            vistos.add(texto)
            por_tipo.setdefault(t, []).append({"dia": d, "agente": a, "tipo": t, "texto": texto, "importancia": i})
        lista = []
        while any(por_tipo.values()):  # uno de cada tipo por ronda, del más importante al menos
            ronda = sorted((v.pop(0) for v in por_tipo.values() if v), key=lambda h: -h["importancia"])
            lista += ronda
        res[lado] = lista
    return res, ultimo


def _escena_persona(ag, lado, usados):
    libres = [a for a in ag if a["lado"] == lado and a["edad"] >= 14 and a["id"] not in usados]
    if not libres:
        return None
    a = random.choice(libres)
    usados.add(a["id"])
    que = VERBO.get(a.get("accion") or "", "sigue con su día")
    texto = f"{a['nombre']}, {a['edad']} años, {que}."
    voz = texto + (f" Piensa: {a['piensa']}" if a.get("piensa") else "")
    return {"lado": lado, "foco": a["id"], "plano": "personaje", "texto": texto, "narracion": voz[:220]}


def guion(mundo, n_escenas, instruccion=""):
    """n_escenas por sociedad a partes iguales, más una escena de apertura común."""
    h, dia = hechos(mundo, dias=config.DIAS_SIM_POR_DIA_REAL)
    e = estado_web() or {}
    ano = e.get("ano") or dia // config.DIAS_POR_ANO + 1
    vivos = {a["id"] for a in e.get("agentes", [])}
    ag = e.get("agentes", [])
    nombres = config.NOMBRE_SOCIEDAD
    orden = ["B", "A"] if random.random() < 0.5 else ["A", "B"]
    escenas, usados, idx = [], set(), {"A": 0, "B": 0}
    for i in range(n_escenas):
        lado = orden[i % 2]
        esc = None
        while idx[lado] < len(h[lado]) and not esc:
            s = h[lado][idx[lado]]
            idx[lado] += 1
            foco = s["agente"] if s["agente"] in vivos and s["agente"] not in usados else None
            if foco:
                usados.add(foco)
            plano = ("rio" if s["tipo"] in ("primer_contacto", "emigración") else "general" if s["tipo"] == "mundo_nuevo"
                     else "personaje" if foco else "aldea")
            esc = {"lado": lado, "foco": foco, "plano": plano, "texto": s["texto"], "narracion": s["texto"]}
        esc = esc or _escena_persona(ag, lado, usados) or {
            "lado": lado, "foco": None, "plano": "aldea", "texto": f"Un día de trabajo entre {nombres[lado]}.",
            "narracion": f"Un día de trabajo entre {nombres[lado]}."}
        escenas.append(esc)
    # una de cada lado con plano amplio para que se vea el mundo (las dos igual)
    for lado in "AB":
        amplias = [x for x in escenas if x["lado"] == lado and x["plano"] == "aldea"]
        if not amplias:
            cand = [x for x in escenas if x["lado"] == lado and x["plano"] == "personaje"]
            if len(cand) > 1:
                cand[-1]["plano"] = "aldea"
    apertura = {"lado": "C", "foco": None, "plano": "marcador", "texto": f"Año {ano}. {config.LEMA}",
                "narracion": f"Año {ano} del experimento. Dos sociedades de inteligencia artificial. Mismo mundo. Valores opuestos."}
    base = {"titular": f"Año {ano}: ¿quién avanza más?", "cierre": "¿Tú eres de Mío o de Nuestro? Síguenos para ver qué pasa.",
            "escenas": [apertura] + escenas, "descripcion": f"{config.PROYECTO} · Año {ano}. {config.LEMA}",
            "hashtags": "#MíoVsNuestro #MioVsNuestro #IA #ExperimentoSocial"}
    if not config.LLM_API_KEY:
        return base, dia
    try:
        pedido = (
            "Eres el guionista neutral de 'Mío vs Nuestro', un experimento con dos sociedades de IA (" + nombres["B"] + " y " + nombres["A"] + "). "
            "Reescribe el guion de un reel vertical en español: tono de documental, frases cortas, gancho fuerte al principio, "
            "SIN opinar sobre qué sociedad es mejor, con el mismo peso para las dos y SIN repetir frases entre escenas. "
            "No menciones partidos ni políticos reales. No inventes hechos que no estén en las escenas.\n"
            f"Escenas (respeta el orden, el número y el lado): {json.dumps(base['escenas'], ensure_ascii=False)}\n"
            + (f"INDICACIONES DE OSCAR PARA ESTA VERSIÓN: {instruccion}\n" if instruccion else "") +
            'Responde SOLO JSON: {"titular": "máx 8 palabras", "escenas": [{"texto": "texto en pantalla, máx 12 palabras", '
            '"narracion": "1-2 frases para la voz, máx 30 palabras"}], "cierre": "1 frase con pregunta al público", '
            '"descripcion": "texto para publicar", "hashtags": "5-8 hashtags"}')
        g = json.loads(llamar_llm([{"role": "user", "content": pedido}], modelo=config.LLM_MODELO_LISTO, max_tokens=1400, temperatura=0.7))
        if len(g.get("escenas", [])) == len(base["escenas"]) and len({x.get("texto") for x in g["escenas"]}) == len(g["escenas"]):
            for nueva, b in zip(g["escenas"], base["escenas"]):
                for k in ("lado", "foco", "plano"):
                    nueva[k] = b[k]  # qué se enseña lo decide el motor, no la IA
            ok, _ = moderacion.revisar_con_ia(json.dumps(g, ensure_ascii=False), llamar_llm)
            if ok:
                return g, dia
    except Exception as err:
        print("Guion con IA no disponible, uso la plantilla:", err)
    return base, dia


# ---------- 2. voz ----------
def voz(texto, ruta):
    piper = os.getenv("PIPER") or shutil.which("piper")
    if texto and piper and Path(piper).exists() and Path(VOZ_PIPER).exists():
        subprocess.run([piper, "--model", VOZ_PIPER, "--output_file", ruta, "--length_scale", "1.05"], input=texto.encode(),
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ruta
    return None  # sin voz instalada: el reel sale con subtítulos y música


def duracion_wav(ruta):
    with wave.open(ruta) as w:
        return w.getnframes() / float(w.getframerate())


# ---------- 3. grabación fotograma a fotograma ----------
def grabar(escenas, titular, carpeta):
    from playwright.sync_api import sync_playwright
    clips = []
    with sync_playwright() as p:
        nav = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
                                executable_path=os.getenv("CHROME") or None)
        for i, e in enumerate(escenas):
            dur = e["dur"]
            params = {"reel": "1", "plano": e.get("plano", "general"), "lado": e["lado"] if e["lado"] in "AB" else "A",
                      "dur": f"{dur:.2f}", "semilla": str(i), "hora": e.get("hora", "0.3")}
            if e.get("foco"):
                params["foco"] = e["foco"]
            if i == 0:
                params.update({"titular": titular, "marcador": "1"})
            pg = nav.new_page(viewport={"width": RENDER[0], "height": RENDER[1]}, device_scale_factor=1)
            pg.goto(URL_WEB + "?" + urllib.parse.urlencode(params))
            pg.wait_for_function("window.listo === true", timeout=120000)
            ruta = str(carpeta / f"clip{i}.mp4")
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                                   "-vf", f"scale={ANCHO}:{ALTO}:flags=lanczos,format=yuv420p", "-c:v", "libx264",
                                   "-preset", "veryfast", "-crf", "19", ruta], stdin=subprocess.PIPE)
            for _ in range(int(round(dur * FPS))):
                pg.evaluate(f"paso({1 / FPS})")
                ff.stdin.write(pg.screenshot(type="jpeg", quality=90))
            ff.stdin.close()
            if ff.wait() != 0:
                raise RuntimeError(f"ffmpeg falló al grabar la escena {i}")
            pg.close()
            clips.append(ruta)
            print(f"  escena {i + 1}/{len(escenas)} grabada ({dur:.1f} s)", flush=True)
        nav.close()
    return clips


# ---------- 4. montaje ----------
def _esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def _texto(carpeta, nombre, t, ancho):
    """Escribe el texto en un archivo, partido en líneas, para que ffmpeg lo dibuje sin problemas de escape."""
    import textwrap
    ruta = carpeta / f"{nombre}.txt"
    lineas = textwrap.wrap(t, ancho)
    if len(lineas) > 4:
        lineas = lineas[:4]
        lineas[-1] = lineas[-1][:ancho - 1].rstrip() + "…"
    ruta.write_text("\n".join(lineas), encoding="utf-8")
    return str(ruta)


def montar(g, clips, carpeta, salida):
    piezas = []
    for i, (e, clip) in enumerate(zip(g["escenas"], clips)):
        dur, audio = e["dur"], e.get("audio")
        tf = _texto(carpeta, f"sub{i}", e.get("texto", ""), 30)
        color = COLOR.get(e["lado"], COLOR["C"])
        nombre = {"A": config.NOMBRE_SOCIEDAD["A"], "B": config.NOMBRE_SOCIEDAD["B"]}.get(e["lado"], config.PROYECTO)
        filtro = (f"[0:v]setpts=PTS-STARTPTS,"
                  f"drawbox=x=40:y=ih*0.69:w=iw-80:h=ih*0.185:color=black@0.55:t=fill,"
                  f"drawbox=x=40:y=ih*0.69:w=12:h=ih*0.185:color={color}@1:t=fill,"
                  f"drawtext=fontfile={FUENTE}:text='{_esc(nombre)}':fontcolor={color}:fontsize=34:x=80:y=h*0.703,"
                  f"drawtext=fontfile={FUENTE}:textfile={tf}:fontcolor=white:fontsize=50:line_spacing=10:x=80:y=h*0.733:"
                  f"alpha='min(1,t/0.35)',"
                  f"drawtext=fontfile={FUENTE}:text='Contenido generado con IA':fontcolor=white@0.85:fontsize=26:"
                  f"box=1:boxcolor=black@0.35:boxborderw=8:x=w-text_w-30:y=h-60,"
                  f"fade=t=in:st=0:d=0.25[v]")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", clip]
        if audio:
            cmd += ["-i", audio, "-filter_complex", filtro + f";[1:a]adelay=250|250,apad=whole_dur={dur}[a]", "-map", "[v]", "-map", "[a]"]
        else:
            cmd += ["-f", "lavfi", "-t", f"{dur}", "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", filtro,
                    "-map", "[v]", "-map", "1:a"]
        pieza = str(carpeta / f"pieza{i}.mp4")
        cmd += ["-t", f"{dur}", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "44100", "-ac", "2", pieza]
        subprocess.run(cmd, check=True)
        piezas.append(pieza)
    # Tarjeta final
    fin = str(carpeta / "fin.mp4")
    cierre_f = _texto(carpeta, "cierre", g.get("cierre", ""), 30)
    lema_f = _texto(carpeta, "lema", config.LEMA, 34)
    logo = config.RAIZ / "reels" / "logo.png"
    entrada_logo = ["-loop", "1", "-t", "3", "-i", str(logo)] if logo.exists() else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=#12181C:s={ANCHO}x{ALTO}:d=3:r={FPS}",
                    "-f", "lavfi", "-t", "3", "-i", "anullsrc=r=44100:cl=stereo", *entrada_logo, "-filter_complex",
                    ("[2:v]scale=460:460,format=rgba[l];[0:v][l]overlay=(W-w)/2:H*0.13[b];[b]" if entrada_logo else "[0:v]") +
                    f"drawtext=fontfile={FUENTE}:text='{_esc(config.PROYECTO)}':fontcolor=white:fontsize=96:x=(w-text_w)/2:y=h*0.38,"
                    f"drawbox=x=(iw/2)-160:y=ih*0.455:w=150:h=10:color={COLOR['B']}@1:t=fill,"
                    f"drawbox=x=(iw/2)+10:y=ih*0.455:w=150:h=10:color={COLOR['A']}@1:t=fill,"
                    f"drawtext=fontfile={FUENTE}:textfile={cierre_f}:fontcolor=#FAC775:fontsize=48:line_spacing=12:x=(w-text_w)/2:y=h*0.50,"
                    f"drawtext=fontfile={FUENTE}:textfile={lema_f}:fontcolor=white@0.8:fontsize=36:line_spacing=10:x=(w-text_w)/2:y=h*0.64,"
                    f"drawtext=fontfile={FUENTE}:text='Contenido generado con IA':fontcolor=white@0.7:fontsize=26:x=(w-text_w)/2:y=h-90,"
                    f"fade=t=in:st=0:d=0.3[v]", "-map", "[v]", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2",
                    "-shortest", fin], check=True)
    piezas.append(fin)
    lista = carpeta / "lista.txt"
    lista.write_text("".join(f"file '{p}'\n" for p in piezas))
    unido = str(carpeta / "unido.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", unido], check=True)
    canciones = sorted(MUSICA.glob("*.mp3")) if MUSICA.exists() else []
    if canciones:  # música libre de derechos que pongas en reels/musica/
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", unido, "-stream_loop", "-1", "-i", str(random.choice(canciones)),
                        "-filter_complex", "[1:a]volume=0.16[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart", salida], check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", unido, "-c", "copy", "-movflags", "+faststart", salida], check=True)


def comprobar_video(ruta):
    """Detecta el fallo de antes: vídeo casi quieto (pantalla congelada) o demasiado corto."""
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", ruta],
                                     capture_output=True, text=True).stdout)
    dur = float(info["format"]["duration"])
    r = subprocess.run(["ffmpeg", "-i", ruta, "-vf", "freezedetect=n=0.003:d=3", "-map", "0:v", "-f", "null", "-"],
                       capture_output=True, text=True)
    congelado = sum(1 for l in r.stderr.splitlines() if "freeze_duration" in l)
    problemas = []
    if dur < 10:
        problemas.append(f"dura solo {dur:.0f} s")
    if congelado > 1:
        problemas.append(f"{congelado} tramos con la imagen congelada")
    return dur, problemas


# ---------- 5. todo junto ----------
def fabricar(tipo="diario", reel_id=None, instruccion="", enviar=True):
    mundo = mundo_actual()
    n, seg = (4, 6.0) if tipo == "diario" else (10, 6.5)  # el episodio dura más de 1 minuto
    g, dia = guion(mundo, n, instruccion)
    SALIDA.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        for i, e in enumerate(g["escenas"]):  # primero la voz: la escena dura lo que dure la frase
            e["audio"] = voz(e.get("narracion", ""), str(carpeta / f"voz{i}.wav"))
            e["dur"] = max(seg if i else 4.5, min(10.0, duracion_wav(e["audio"]) + 0.9)) if e["audio"] else (seg if i else 4.5)
            e["hora"] = "0.62" if i == len(g["escenas"]) - 1 and tipo == "episodio" else "0.3"
        clips = grabar(g["escenas"], g["titular"], carpeta)
        bd = bd_reels()
        if reel_id is None:
            cur = bd.execute("INSERT INTO reels(creado, mundo, dia, estado) VALUES(?,?,?,?)", (time.time(), mundo, dia, "montando"))
            reel_id = cur.lastrowid
            version = 1
        else:
            version = (bd.execute("SELECT version FROM reels WHERE id=?", (reel_id,)).fetchone()[0] or 1) + 1
        salida = str(SALIDA / f"reel_{reel_id}_v{version}.mp4")
        montar(g, clips, carpeta, salida)
    dur, problemas = comprobar_video(salida)
    for e in g["escenas"]:
        e.pop("audio", None)
    texto = f"{g.get('descripcion', '')}\n\n{g.get('hashtags', '')}\n\nContenido generado con IA."
    bd.execute("UPDATE reels SET ruta=?, guion=?, texto=?, estado='pendiente', version=? WHERE id=?",
               (salida, json.dumps(g, ensure_ascii=False), texto, version, reel_id))
    bd.commit()
    print(f"Reel {reel_id} v{version}: {dur:.0f} s, montado en {(time.time() - t0) / 60:.1f} min" +
          (f" · AVISO: {', '.join(problemas)}" if problemas else ""), flush=True)
    if enviar:
        aviso = f"\n\n⚠️ Revisión automática: {', '.join(problemas)}." if problemas else ""
        enviar_para_aprobar(reel_id, salida, texto + aviso, tipo, version)
    return salida


def enviar_para_aprobar(reel_id, ruta, texto, tipo, version):
    if not (config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID):
        print(f"Reel listo (sin Telegram configurado): {ruta}")
        return
    import bot
    botones = [[{"text": "✅ Aprobar", "callback_data": f"reel:aprobar:{reel_id}"},
                {"text": "✏️ Cambiar", "callback_data": f"reel:cambiar:{reel_id}"}]]
    bot.enviar_video(ruta, f"Reel {tipo} nº {reel_id} (versión {version})\n\n{texto}", botones)


def rehacer():
    bd = bd_reels()
    for ident, instr in bd.execute("SELECT id, instruccion FROM reels WHERE estado='rehacer'").fetchall():
        bd.execute("UPDATE reels SET estado='montando' WHERE id=?", (ident,)); bd.commit()
        fabricar("diario", reel_id=ident, instruccion=instr or "")


def bloqueo():
    """Evita que se monten dos reels a la vez (cada uno tarda varios minutos)."""
    import fcntl
    f = open(config.DATOS / "reels.lock", "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Ya se está montando otro reel; lo dejo para la próxima vez.")
        sys.exit(0)
    return f


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "diario"
    config.DATOS.mkdir(exist_ok=True)
    _cerrojo = bloqueo()
    if modo == "rehacer":
        rehacer()
    elif modo == "prueba":
        print(fabricar(sys.argv[2] if len(sys.argv) > 2 else "diario", enviar=False))
    else:
        print(fabricar(modo))
