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
import re
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
RENDER = (int(os.getenv("REEL_RENDER_ANCHO", "640")), int(os.getenv("REEL_RENDER_ALTO", "1136")))  # se dibuja así y se escala
FPS = int(os.getenv("REEL_FPS", "24"))
# En los planos abiertos las sombras casi no se notan y son un 30 % del tiempo de dibujo: se quitan ahí.
PLANOS_SIN_SOMBRAS = set(os.getenv("REEL_PLANOS_SIN_SOMBRAS", "general,marcador,rio").split(","))
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


# ---------- lo que se ve en cada escena: la acción que se narra ----------
MATERIAL_A_OBJETO = {"comida": "frutos", "carne": "carne", "pieles": "pieles", "madera": "madera", "piedra": "piedra",
                     "pescado": "pescado", "fibra": "fibra", "arcilla": "arcilla", "metal": "metal", "carbon": "carbon", "carbón": "carbon"}
ACCIONES_DE_DOS = {"trueque", "trueque_rechazado", "regalo", "robo", "habla", "enseñanza", "pareja", "nacimiento"}


def _objetos_del_texto(tipo, texto):
    """Qué llevan en las manos según lo que dice el suceso («cambia madera por pescado» → madera y pescado)."""
    t = (texto or "").lower()
    m = re.search(r"cambia (\w+) por (\w+)", t)
    if m:
        return MATERIAL_A_OBJETO.get(m.group(1)), MATERIAL_A_OBJETO.get(m.group(2))
    if tipo == "caza":
        return "carne", "pieles"
    for palabra in re.findall(r"\w+", t):
        if palabra in MATERIAL_A_OBJETO:
            return MATERIAL_A_OBJETO[palabra], None
    return None, None


def _companero(texto, foco, ag):
    """El otro habitante que nombra el suceso (para ponerlos frente a frente)."""
    nombre_foco = next((a["nombre"] for a in ag if a["id"] == foco), None)
    resto = (texto or "").replace(nombre_foco, "", 1) if nombre_foco else (texto or "")
    for a in sorted(ag, key=lambda a: -len(a["nombre"])):  # «Xabier 2» antes que «Xabier»
        if a["id"] != foco and re.search(r"\b" + re.escape(a["nombre"]) + r"\b(?! \d)", resto):
            return a["id"]
    return None


def _accion_de_escena(esc, s, ag):
    """Añade a la escena qué hay que escenificar: accion, con (compañero) y los objetos (prop, prop2)."""
    if not esc.get("foco"):
        return esc
    esc["accion"] = s["tipo"]
    if s["tipo"] in ACCIONES_DE_DOS:
        otro = _companero(s["texto"], esc["foco"], ag)
        if otro:
            esc["con"] = otro
    p1, p2 = _objetos_del_texto(s["tipo"], s["texto"])
    if p1:
        esc["prop"] = p1
    if p2 and s["tipo"] != "caza":
        esc["prop2"] = p2
    return esc


def _escena_persona(ag, lado, usados):
    libres = [a for a in ag if a["lado"] == lado and a["edad"] >= 14 and a["id"] not in usados]
    if not libres:
        return None
    a = random.choice(libres)
    usados.add(a["id"])
    que = VERBO.get(a.get("accion") or "", "sigue con su día")
    texto = f"{a['nombre']}, {a['edad']} años, {que}."
    voz = texto + (f" Piensa: {a['piensa']}" if a.get("piensa") else "")
    return {"lado": lado, "foco": a["id"], "plano": "personaje", "texto": texto, "narracion": voz[:220], "accion": a.get("accion") or ""}


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
                     else "aldea" if s["tipo"] == "construccion_nueva" else "personaje" if foco else "aldea")
            esc = _accion_de_escena({"lado": lado, "foco": foco, "plano": plano, "texto": s["texto"], "narracion": s["texto"]}, s, ag)
        esc = esc or _escena_persona(ag, lado, usados) or {
            "lado": lado, "foco": None, "plano": "aldea", "texto": f"Un día de trabajo entre {nombres[lado]}.",
            "narracion": f"Un día de trabajo entre {nombres[lado]}."}
        escenas.append(esc)
    # una de cada lado con plano amplio para que se vea el mundo (las dos igual)
    for lado in "AB":
        amplias = [x for x in escenas if x["lado"] == lado and x["plano"] == "aldea"]
        if not amplias:
            cand = [x for x in escenas if x["lado"] == lado and x["plano"] == "personaje" and x.get("accion") not in ACCIONES_DE_DOS]
            if len(cand) > 1:
                cand[-1]["plano"] = "aldea"
    apertura = {"lado": "C", "foco": None, "plano": "marcador", "texto": f"Año {ano}. {config.LEMA}",
                "narracion": f"Año {ano} del experimento. Dos sociedades de inteligencia artificial. Mismo mundo. Valores opuestos."}
    base = {"titular": f"Año {ano}: ¿quién avanza más?", "cierre": "¿Tú eres de Mío o de Nuestro? Síguenos para ver qué pasa.",
            "escenas": [apertura] + escenas, "descripcion": f"{config.PROYECTO} · Año {ano}. {config.LEMA}",
            "hashtags": "#MíoVsNuestro #MioVsNuestro #IA #ExperimentoSocial"}
    if not config.LLM_API_KEY:
        return base, dia
    g = _guion_ia(base, h, e, orden, ano, dia, instruccion)
    return (g or base), dia


def _contexto_sociedad(lado, h, e):
    """Lo que el guionista necesita para ENTENDER el día de una sociedad (igual de detallado en las dos)."""
    soc = (e.get("sociedades") or {}).get(lado, {})
    m = soc.get("metricas", {})
    datos = [f"{k.replace('_', ' ')}: {m[k]}" for k in ("poblacion", "bienestar", "comida_total", "inventos", "nacimientos",
                                                       "muertes", "conflictos", "con_refugio", "parejas", "territorio") if k in m]
    inventos = ", ".join(i["nombre"] for i in soc.get("inventos", [])[-6:]) or "ninguno todavía"
    sucesos = "\n".join(f"   - día {x['dia']}: {x['texto']}" for x in h.get(lado, [])[:8]) or "   - (sin sucesos destacados)"
    cronica = (soc.get("cronica") or "").replace("*", "").strip()
    return (f"«{config.NOMBRE_SOCIEDAD[lado]}» ({config.SUBTITULO_SOCIEDAD[lado]}) · época: {soc.get('epoca', e.get('epoca', '?'))}\n"
            f"  Datos: {'; '.join(datos)}\n  Inventos: {inventos}\n"
            f"  Crónica del último día: {cronica or '(sin crónica)'}\n  Sucesos recientes:\n{sucesos}")


def _revisar_guion(g, base):
    """Devuelve una lista de problemas (vacía = guion válido)."""
    if not isinstance(g, dict):
        return ["la respuesta no es un objeto JSON"]
    esc = g.get("escenas")
    if not isinstance(esc, list):
        return ["falta la lista «escenas»"]
    fallos = []
    if len(esc) != len(base["escenas"]):
        fallos.append(f"hay {len(esc)} escenas y deben ser exactamente {len(base['escenas'])}")
    for n, x in enumerate(esc, 1):
        if not isinstance(x, dict) or not str(x.get("texto", "")).strip() or not str(x.get("narracion", "")).strip():
            fallos.append(f"la escena {n} no tiene «texto» y «narracion»")
    textos = [str(x.get("texto", "")).strip().lower() for x in esc if isinstance(x, dict)]
    if len(set(textos)) != len(textos):
        fallos.append("hay escenas con el mismo texto en pantalla")
    for k in ("titular", "cierre"):
        if not str(g.get(k, "")).strip():
            fallos.append(f"falta «{k}»")
    return fallos


def _guion_ia(base, h, e, orden, ano, dia, instruccion=""):
    """Guion escrito por la IA a partir de lo que de verdad pasó. Devuelve None si no sale uno válido
    (y explica en el log por qué), para que el reel salga igualmente con la plantilla."""
    from sim.cerebro import llamar_json
    nombres = config.NOMBRE_SOCIEDAD
    etiqueta = {"A": nombres["A"], "B": nombres["B"], "C": "las dos (apertura)"}
    lista = "\n".join(f"{n}. [{etiqueta[x['lado']]} · plano {x['plano']}] {x['narracion']}"
                       for n, x in enumerate(base["escenas"], 1))
    sistema = (
        "Eres el guionista de «Mío vs Nuestro», un experimento real que se emite en TikTok, Instagram y YouTube: dos "
        "sociedades de agentes de IA viven en el mismo mundo simulado desde la prehistoria, con los mismos recursos y "
        "valores opuestos (" + "; ".join(f"{nombres[l]}: {config.SUBTITULO_SOCIEDAD[l]}" for l in orden) + "). El público sigue la historia día a día, como una serie documental.\n"
        "Cómo escribes:\n"
        "- Español de España, tono de documental de naturaleza: concreto, visual, con ritmo. Frases cortas.\n"
        "- La primera escena es el gancho: una pregunta o un contraste real que haga quedarse a mirar.\n"
        "- Cada escena cuenta algo distinto y concreto (quién, qué hace, qué consigue o qué le preocupa). Nada de "
        "frases vacías como «un día más de trabajo».\n"
        "- Hilo narrativo: las escenas se encadenan y el cierre retoma el gancho.\n"
        "- NEUTRALIDAD OBLIGATORIA: mismo peso y mismo tono para las dos sociedades; nunca insinúes cuál es mejor ni "
        "uses adjetivos que la juzguen. Muestra, no opines.\n"
        "- Usa SOLO hechos que aparezcan en el material. Puedes elegir, ordenar y explicar, pero no inventar.\n"
        "- Ni partidos ni políticos reales, ni violencia gráfica.\n"
        "Respondes siempre con un único objeto JSON válido, sin texto antes ni después.")
    contexto = "\n\n".join(_contexto_sociedad(l, h, e) for l in orden)
    pedido = (
        f"Reel del año {ano} (día {dia}) del experimento. Primer contacto entre sociedades: "
        f"{'sí' if e.get('contacto') else 'todavía no'}.\n\n"
        f"MATERIAL DE CADA SOCIEDAD (para que entiendas qué está pasando):\n{contexto}\n\n"
        f"ESCENAS QUE SE VAN A GRABAR ({len(base['escenas'])}, en este orden; la imagen ya está decidida y muestra a la "
        f"sociedad y el plano indicados, así que el texto de cada escena debe hablar de ESA sociedad):\n{lista}\n\n"
        + (f"INDICACIONES DE OSCAR PARA ESTA VERSIÓN (tienen prioridad): {instruccion}\n\n" if instruccion else "") +
        f"Devuelve este JSON con exactamente {len(base['escenas'])} escenas, en el mismo orden:\n"
        '{"titular": "máx. 8 palabras", "escenas": [{"texto": "texto en pantalla, máx. 12 palabras", '
        '"narracion": "1-2 frases para la voz, máx. 30 palabras"}], "cierre": "1 frase con pregunta al público", '
        '"descripcion": "texto para publicar, 2-3 frases", "hashtags": "5-8 hashtags"}')
    mensajes = [{"role": "system", "content": sistema}, {"role": "user", "content": pedido}]
    for vuelta in (1, 2):
        registro = []
        try:
            g = llamar_json(mensajes, modelo=config.LLM_MODELO_LISTO, max_tokens=3000, temperatura=0.7,
                            registro=registro, timeout=120)
        except Exception as err:
            print("Guion con IA no disponible, uso la plantilla:", err)
            return None
        for r in registro:
            print("  aviso del guion:", r)
        fallos = _revisar_guion(g, base)
        if not fallos:
            break
        print(f"  guion de la IA no válido (vuelta {vuelta}): {'; '.join(fallos)}")
        if vuelta == 2:
            print("Guion con IA descartado tras corregirlo una vez; uso la plantilla.")
            return None
        mensajes = mensajes + [{"role": "assistant", "content": json.dumps(g, ensure_ascii=False)},
                               {"role": "user", "content": "Corrige estos problemas y devuelve el JSON completo otra vez: "
                                + "; ".join(fallos)}]
    for nueva, b in zip(g["escenas"], base["escenas"]):
        for k in ("lado", "foco", "plano", "accion", "con", "prop", "prop2"):
            if k in b:
                nueva[k] = b[k]  # qué se enseña lo decide el motor, no la IA
    for k in ("descripcion", "hashtags"):
        g[k] = g.get(k) or base[k]
    try:
        ok, motivo = moderacion.revisar_con_ia(json.dumps(g, ensure_ascii=False), llamar_llm)
    except Exception as err:
        ok, motivo = False, f"no se pudo moderar ({err})"
    if not ok:
        print("Guion con IA retenido por la moderación, uso la plantilla:", motivo)
        return None
    print(f"Guion con IA listo: «{g.get('titular')}»")
    g["_ia"] = True
    return g


# ---------- 2. voz ----------
# Proveedor de la voz del narrador (VOZ_PROVEEDOR en .env): azure (gratis hasta 0,5 M caracteres/mes),
# elevenlabs (de pago, la más natural) o piper (local y gratis, la más robótica). Si el elegido falla o se
# pasa del cupo gratis, se usa Piper para que el reel salga igual.
VOZ_PROVEEDOR = os.getenv("VOZ_PROVEEDOR", "azure" if os.getenv("AZURE_SPEECH_KEY") else "piper")
VOZ_AZURE = os.getenv("VOZ_AZURE", "es-ES-AlvaroNeural")
CUPO_AZURE = int(os.getenv("CUPO_AZURE_CARACTERES", "450000"))  # margen bajo los 500.000 gratis


def _uso_voz(sumar=0):
    """Caracteres enviados este mes al proveedor de voz (para no salirse del plan gratis)."""
    ruta = config.DATOS / "voz_uso.json"
    mes = time.strftime("%Y-%m")
    try:
        d = json.loads(ruta.read_text())
    except Exception:
        d = {}
    if d.get("mes") != mes:
        d = {"mes": mes, "caracteres": 0}
    if sumar:
        d["caracteres"] += sumar
        ruta.write_text(json.dumps(d))
    return d["caracteres"]


def _voz_azure(texto, ruta):
    import urllib.request
    from xml.sax.saxutils import escape
    region, clave = os.getenv("AZURE_SPEECH_REGION", "westeurope"), os.getenv("AZURE_SPEECH_KEY")
    if not clave or _uso_voz() + len(texto) > CUPO_AZURE:
        return None
    ssml = (f'<speak version="1.0" xml:lang="es-ES"><voice name="{VOZ_AZURE}">'
            f'<prosody rate="-4%">{escape(texto)}</prosody></voice></speak>')
    # Se pide en MP3 (8 veces más ligero que WAV) y se convierte a WAV con ffmpeg. La descarga se lee por trozos
    # y, si se corta a medias (IncompleteRead), se reintenta con espera creciente y, desde el tercer intento,
    # con un MP3 más ligero (48 kbit/s, de sobra para una voz), que tiene menos que descargar.
    mp3 = ruta + ".mp3"
    ultimo = None
    for intento in range(5):
        formato = "audio-24khz-96kbitrate-mono-mp3" if intento < 2 else "audio-24khz-48kbitrate-mono-mp3"
        try:
            req = urllib.request.Request(f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1", data=ssml.encode("utf-8"),
                                         headers={"Ocp-Apim-Subscription-Key": clave, "Content-Type": "application/ssml+xml",
                                                  "X-Microsoft-OutputFormat": formato, "User-Agent": "miovsnuestro",
                                                  "Connection": "close"})
            trozos = []
            with urllib.request.urlopen(req, timeout=90) as r:
                while True:
                    t = r.read(16384)
                    if not t:
                        break
                    trozos.append(t)
            datos = b"".join(trozos)
            if len(datos) < 2000:
                raise RuntimeError(f"audio demasiado corto ({len(datos)} bytes)")
            Path(mp3).write_bytes(datos)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "24000", "-ac", "1", ruta], check=True)
            _uso_voz(len(texto))
            return ruta
        except Exception as err:
            ultimo = err
            time.sleep((2, 5, 10, 20, 0)[intento])
    raise RuntimeError(f"{ultimo} (tras 5 intentos)")


def _voz_elevenlabs(texto, ruta):
    import urllib.request
    clave, voz_id = os.getenv("ELEVENLABS_API_KEY"), os.getenv("ELEVENLABS_VOZ")
    if not (clave and voz_id):
        return None
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voz_id}?output_format=pcm_24000",
                                 data=json.dumps({"text": texto, "model_id": os.getenv("ELEVENLABS_MODELO", "eleven_multilingual_v2")}).encode(),
                                 headers={"xi-api-key": clave, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        pcm = r.read()
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    _uso_voz(len(texto))
    return ruta


def _voz_piper(texto, ruta):
    piper = os.getenv("PIPER") or shutil.which("piper")
    if piper and Path(piper).exists() and Path(VOZ_PIPER).exists():
        subprocess.run([piper, "--model", VOZ_PIPER, "--output_file", ruta, "--length_scale", "1.05"], input=texto.encode(),
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ruta
    return None


def voz(texto, ruta, proveedor_forzado=None):
    """Devuelve (ruta del wav o None, proveedor que la hizo)."""
    if not texto:
        return None, None
    nombre = proveedor_forzado or VOZ_PROVEEDOR
    proveedor = {"azure": _voz_azure, "elevenlabs": _voz_elevenlabs}.get(nombre)
    if proveedor:
        try:
            r = proveedor(texto, ruta)
            if r:
                return r, nombre
            print(f"Voz {nombre}: sin clave o cupo del mes agotado; uso Piper.", flush=True)
        except Exception as err:
            print(f"Voz {nombre} no disponible ({err}); uso Piper.", flush=True)
    r = _voz_piper(texto, ruta)  # sin voz instalada: el reel sale con subtítulos y música
    return r, ("piper" if r else None)


def voces_del_reel(escenas, carpeta):
    """Todo el reel con LA MISMA voz: si alguna escena no sale con la voz buena, se reintenta al final y,
    si sigue sin salir, se rehace todo el reel con Piper (mezclar dos voces en un reel suena a error)."""
    quien = {}
    for i, e in enumerate(escenas):
        e["audio"], quien[i] = voz(e.get("narracion", ""), str(carpeta / f"voz{i}.wav"))
    hechas = {q for q in quien.values() if q}
    if len(hechas) <= 1:
        return next(iter(hechas), None)
    buena = VOZ_PROVEEDOR
    for i, e in enumerate(escenas):
        if quien[i] and quien[i] != buena:
            time.sleep(15)
            print(f"  reintento la voz de la escena {i + 1} con {buena}", flush=True)
            e["audio"], quien[i] = voz(e.get("narracion", ""), str(carpeta / f"voz{i}.wav"), buena)
    if len({q for q in quien.values() if q}) > 1:
        print("  la voz buena no sale en todas las escenas: hago todo el reel con Piper para que no se mezclen", flush=True)
        for i, e in enumerate(escenas):
            if e.get("narracion"):
                e["audio"] = _voz_piper(e["narracion"], str(carpeta / f"voz{i}.wav"))
        return "piper (respaldo)"
    return buena


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
                for k in ("accion", "con", "prop", "prop2"):  # que se vea la acción que se narra
                    if e.get(k):
                        params[k] = e[k]
            if params["plano"] in PLANOS_SIN_SOMBRAS:
                params["sombras"] = "0"
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
        voz_usada = voces_del_reel(g["escenas"], carpeta)  # primero la voz: la escena dura lo que dure la frase
        for i, e in enumerate(g["escenas"]):
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
    if voz_usada and voz_usada != VOZ_PROVEEDOR and VOZ_PROVEEDOR != "piper":
        problemas.append(f"voz de respaldo ({voz_usada}) porque {VOZ_PROVEEDOR} no respondió")
    if not g.get("_ia"):
        problemas.append("guion de plantilla (la IA no dio un guion válido; mira reels.log)")
    g.pop("_ia", None)
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


def bloqueo(esperar_min=0):
    """Evita que se monten dos reels a la vez (cada uno tarda bastantes minutos).
    El reel diario y el episodio esperan su turno (hasta `esperar_min`) en vez de perderse ese día."""
    import fcntl
    f = open(config.DATOS / "reels.lock", "w")
    limite = time.time() + esperar_min * 60
    aviso = False
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except OSError:
            if time.time() >= limite:
                print("Ya se está montando otro reel; lo dejo para la próxima vez.", flush=True)
                sys.exit(0)
            if not aviso:
                print(f"Hay otro reel montándose; espero mi turno (hasta {esperar_min} min).", flush=True)
                aviso = True
            time.sleep(30)


def hay_que_rehacer():
    try:
        return bd_reels().execute("SELECT COUNT(*) FROM reels WHERE estado='rehacer'").fetchone()[0] > 0
    except Exception:
        return True  # si no se puede mirar, que lo intente como antes


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "diario"
    config.DATOS.mkdir(exist_ok=True)
    if modo == "rehacer":
        if not hay_que_rehacer():
            sys.exit(0)  # cron lo lanza cada 10 min: sin nada pendiente no hace nada ni escribe en el log
        _cerrojo = bloqueo()
        rehacer()
    elif modo == "prueba":
        _cerrojo = bloqueo()
        print(fabricar(sys.argv[2] if len(sys.argv) > 2 else "diario", enviar=False))
    else:
        _cerrojo = bloqueo(esperar_min=120)
        print(fabricar(modo))
