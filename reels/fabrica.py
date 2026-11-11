"""Fábrica de reels: guion → grabación del mundo → voz → montaje → Telegram para aprobar.

Uso (lo lanza cron en el servidor):
    python -m reels.fabrica diario          # reel corto del día (≈30 s)
    python -m reels.fabrica episodio        # episodio de más de 1 minuto (para TikTok/YouTube)
    python -m reels.fabrica rehacer         # vuelve a montar los reels a los que pediste cambios

Todo es igual para las dos sociedades: mismo tiempo en pantalla y mismo tono. Cada reel lleva la
etiqueta «Contenido generado con IA».
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
from pathlib import Path
from sim import config
from sim.cerebro import llamar_llm
from sim import moderacion

SALIDA = config.RAIZ / "reels" / "salida"
MUSICA = config.RAIZ / "reels" / "musica"
URL_WEB = os.getenv("REEL_URL", "http://127.0.0.1/")
FUENTE = os.getenv("REEL_FUENTE", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
VOZ_PIPER = os.getenv("VOZ_PIPER", str(config.RAIZ / "voces" / "es_ES-davefx-medium.onnx"))
ANCHO, ALTO = 1080, 1920


def mundo_actual():
    return (config.RAIZ / ".mundo").read_text().strip() if (config.RAIZ / ".mundo").exists() else "pruebas"


def bd_reels():
    import bot
    return bot.bd_reels()


# ---------- 1. guion ----------
def hechos(mundo, dias):
    bd = sqlite3.connect(config.DATOS / f"{mundo}.db")
    ultimo = bd.execute("SELECT MAX(dia) FROM sucesos WHERE mundo=?", (mundo,)).fetchone()[0] or 0
    res = {}
    for lado in "AB":
        filas = bd.execute("SELECT dia, agente, tipo, texto, importancia FROM sucesos WHERE mundo=? AND lado=? AND dia>? "
                           "AND importancia>=3 ORDER BY importancia DESC, dia DESC LIMIT 8", (mundo, lado, ultimo - dias)).fetchall()
        res[lado] = [{"dia": d, "agente": a, "tipo": t, "texto": moderacion.revisar(x)[0], "importancia": i} for d, a, t, x, i in filas]
    return res, ultimo


def guion(mundo, n_escenas, instruccion=""):
    h, dia = hechos(mundo, dias=config.DIAS_SIM_POR_DIA_REAL)
    try:
        ano = json.loads((config.WEB / "estado.json").read_text())["ano"]
    except Exception:
        ano = dia // config.DIAS_POR_ANO + 1
    nombres = config.NOMBRE_SOCIEDAD
    # Alterna sociedades para que las dos tengan el mismo tiempo en pantalla.
    orden = ["B", "A"] if random.random() < 0.5 else ["A", "B"]
    elegidos = []
    for i in range(n_escenas):
        lado = orden[i % 2]
        lista = h[lado]
        if lista:
            elegidos.append({"lado": lado, **lista[(i // 2) % len(lista)]})
        else:
            elegidos.append({"lado": lado, "agente": None, "texto": f"Un día tranquilo entre {nombres[lado]}.", "tipo": "calma"})
    base = {"titular": f"Año {ano}: ¿quién avanza más?", "cierre": "¿Tú eres de Mío o de Nuestro? Síguenos para ver qué pasa.",
            "escenas": [{"lado": e["lado"], "foco": e.get("agente"), "texto": e["texto"][:90], "narracion": e["texto"]} for e in elegidos],
            "descripcion": f"{config.PROYECTO} · Año {ano}. {config.LEMA}", "hashtags": "#MíoVsNuestro #MioVsNuestro #IA #ExperimentoSocial"}
    if not config.LLM_API_KEY:
        return base, dia
    try:
        pedido = (
            "Eres el guionista neutral de 'Mío vs Nuestro', un experimento con dos sociedades de IA (" + nombres["B"] + " y " + nombres["A"] + "). "
            "Escribe el guion de un reel vertical en español: tono de documental, frases cortas, gancho fuerte al principio, "
            "SIN opinar sobre qué sociedad es mejor y con el mismo tiempo para las dos. No menciones partidos ni políticos reales.\n"
            f"Escenas (respeta el orden y el 'foco'): {json.dumps(base['escenas'], ensure_ascii=False)}\n"
            + (f"INDICACIONES DE OSCAR PARA ESTA VERSIÓN: {instruccion}\n" if instruccion else "") +
            'Responde SOLO JSON: {"titular": "máx 8 palabras", "escenas": [{"lado": "A/B", "foco": id, "texto": "texto en pantalla, máx 12 palabras", '
            '"narracion": "1-2 frases para la voz"}], "cierre": "1 frase con pregunta al público", "descripcion": "texto para publicar", "hashtags": "5-8 hashtags"}')
        g = json.loads(llamar_llm([{"role": "user", "content": pedido}], modelo=config.LLM_MODELO_LISTO, max_tokens=900, temperatura=0.7))
        if len(g.get("escenas", [])) == len(base["escenas"]):
            for e, b in zip(g["escenas"], base["escenas"]):
                e["foco"], e["lado"] = b["foco"], b["lado"]  # el foco lo decide el motor, no la IA
            ok, _ = moderacion.revisar_con_ia(json.dumps(g, ensure_ascii=False), llamar_llm)
            if ok:
                return g, dia
    except Exception as e:
        print("Guion con IA no disponible, uso la plantilla:", e)
    return base, dia


# ---------- 2. grabación ----------
def grabar(escenas, titular, carpeta, segundos):
    from playwright.sync_api import sync_playwright
    clips = []
    with sync_playwright() as p:
        nav = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
                                executable_path=os.getenv("CHROME") or None)
        for i, e in enumerate(escenas):
            params = {"reel": "1", "rotar": "1", "lado": e["lado"]}
            if e.get("foco"):
                params["foco"] = e["foco"]
            if i == 0:
                params.update({"titular": titular, "marcador": "1"})
            params["semilla"] = str(i)
            ctx = nav.new_context(viewport={"width": ANCHO, "height": ALTO}, device_scale_factor=1,
                                  record_video_dir=str(carpeta), record_video_size={"width": ANCHO, "height": ALTO})
            pg = ctx.new_page()
            pg.goto(URL_WEB + "?" + urllib.parse.urlencode(params))
            pg.wait_for_function("window.listo === true", timeout=60000)
            pg.wait_for_timeout(int(segundos * 1000) + 800)
            ruta = pg.video.path()
            ctx.close()
            clips.append(ruta)
        nav.close()
    return clips


# ---------- 3. voz ----------
def voz(texto, ruta):
    piper = os.getenv("PIPER") or shutil.which("piper")
    if piper and Path(piper).exists() and Path(VOZ_PIPER).exists():
        subprocess.run([piper, "--model", VOZ_PIPER, "--output_file", ruta], input=texto.encode(), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ruta
    return None  # sin voz instalada: el reel sale con subtítulos y música


# ---------- 4. montaje ----------
def _esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def _texto(carpeta, nombre, t, ancho):
    """Escribe el texto en un archivo, partido en líneas, para que ffmpeg lo dibuje sin problemas de escape."""
    import textwrap
    ruta = carpeta / f"{nombre}.txt"
    ruta.write_text("\n".join(textwrap.wrap(t, ancho)[:3]), encoding="utf-8")
    return str(ruta)


def montar(g, clips, carpeta, segundos, salida):
    piezas = []
    for i, (e, clip) in enumerate(zip(g["escenas"], clips)):
        audio = voz(e.get("narracion", ""), str(carpeta / f"voz{i}.wav"))
        tf = _texto(carpeta, f"sub{i}", e.get("texto", ""), 24)
        filtro = (f"[0:v]trim=start=0.8:duration={segundos},setpts=PTS-STARTPTS,scale={ANCHO}:{ALTO},fps=30,"
                  f"drawbox=x=0:y=ih*0.66:w=iw:h=ih*0.16:color=black@0.5:t=fill,"
                  f"drawtext=fontfile={FUENTE}:textfile={tf}:fontcolor=white:fontsize=60:line_spacing=14:x=(w-text_w)/2:y=h*0.69:"
                  f"enable='gte(t,0.3)',"
                  f"drawtext=fontfile={FUENTE}:text='Contenido generado con IA':fontcolor=white@0.85:fontsize=26:x=w-text_w-30:y=40[v]")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", clip]
        if audio:
            cmd += ["-i", audio, "-filter_complex", filtro + f";[1:a]apad=whole_dur={segundos}[a]", "-map", "[v]", "-map", "[a]"]
        else:
            cmd += ["-f", "lavfi", "-t", str(segundos), "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", filtro,
                    "-map", "[v]", "-map", "1:a"]
        pieza = str(carpeta / f"pieza{i}.mp4")
        cmd += ["-t", str(segundos), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "44100", pieza]
        subprocess.run(cmd, check=True)
        piezas.append(pieza)
    # Tarjeta final
    fin = str(carpeta / "fin.mp4")
    cierre_f = _texto(carpeta, "cierre", g.get("cierre", ""), 30)
    lema_f = _texto(carpeta, "lema", config.LEMA, 34)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=#12181C:s={ANCHO}x{ALTO}:d=3:r=30",
                    "-f", "lavfi", "-t", "3", "-i", "anullsrc=r=44100:cl=stereo", "-vf",
                    f"drawtext=fontfile={FUENTE}:text='{_esc(config.PROYECTO)}':fontcolor=white:fontsize=96:x=(w-text_w)/2:y=h*0.40,"
                    f"drawtext=fontfile={FUENTE}:textfile={cierre_f}:fontcolor=#FAC775:fontsize=48:line_spacing=12:x=(w-text_w)/2:y=h*0.50,"
                    f"drawtext=fontfile={FUENTE}:textfile={lema_f}:fontcolor=white@0.8:fontsize=36:line_spacing=10:x=(w-text_w)/2:y=h*0.64",
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-shortest", fin], check=True)
    piezas.append(fin)
    lista = carpeta / "lista.txt"
    lista.write_text("".join(f"file '{p}'\n" for p in piezas))
    unido = str(carpeta / "unido.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", unido], check=True)
    canciones = sorted(MUSICA.glob("*.mp3")) if MUSICA.exists() else []
    if canciones:  # música libre de derechos que pongas en reels/musica/
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", unido, "-stream_loop", "-1", "-i", str(random.choice(canciones)),
                        "-filter_complex", "[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=first[a]",
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", salida], check=True)
    else:
        shutil.copy(unido, salida)


# ---------- 5. todo junto ----------
def fabricar(tipo="diario", reel_id=None, instruccion=""):
    mundo = mundo_actual()
    n, seg = (4, 6) if tipo == "diario" else (10, 6.5)  # el episodio dura más de 1 minuto
    g, dia = guion(mundo, n, instruccion)
    SALIDA.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        clips = grabar(g["escenas"], g["titular"], carpeta, seg)
        bd = bd_reels()
        if reel_id is None:
            cur = bd.execute("INSERT INTO reels(creado, mundo, dia, estado) VALUES(?,?,?,?)", (time.time(), mundo, dia, "montando"))
            reel_id = cur.lastrowid
            version = 1
        else:
            version = (bd.execute("SELECT version FROM reels WHERE id=?", (reel_id,)).fetchone()[0] or 1) + 1
        salida = str(SALIDA / f"reel_{reel_id}_v{version}.mp4")
        montar(g, clips, carpeta, seg, salida)
    texto = f"{g.get('descripcion', '')}\n\n{g.get('hashtags', '')}\n\nContenido generado con IA."
    bd.execute("UPDATE reels SET ruta=?, guion=?, texto=?, estado='pendiente', version=? WHERE id=?",
               (salida, json.dumps(g, ensure_ascii=False), texto, version, reel_id))
    bd.commit()
    enviar_para_aprobar(reel_id, salida, texto, tipo, version)
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


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "diario"
    if modo == "rehacer":
        rehacer()
    else:
        print(fabricar(modo))
