"""Bot de Telegram de Mío vs Nuestro. Solo obedece al chat de Oscar.

Qué hace:
- Te manda cada reel terminado con dos botones: «Aprobar» y «Cambiar».
  · Aprobar: en la fase privada se guarda para el lanzamiento; después, se publica (o te llega listo
    para compartir si la publicación automática aún no está aprobada por la plataforma).
  · Cambiar: te pregunta qué quieres cambiar, y la fábrica lo vuelve a montar con tus indicaciones.
- Te manda las propuestas de ampliación con «Aprobar» y «Rechazar». Nada se aplica sin tu sí.
- Comandos: /estado /pausa /reanudar /propuestas /reels /ayuda
"""
import json
import sqlite3
import subprocess
import time
import urllib.parse
import urllib.request
from sim import config

API = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}"
REELS_BD = config.DATOS / "reels.db"


def llamar(metodo, **params):
    datos = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items()}).encode()
    with urllib.request.urlopen(f"{API}/{metodo}", data=datos, timeout=70) as r:
        return json.loads(r.read())


def enviar(texto, botones=None):
    params = {"chat_id": config.TELEGRAM_CHAT_ID, "text": texto}
    if botones:
        params["reply_markup"] = {"inline_keyboard": botones}
    return llamar("sendMessage", **params)


def enviar_video(ruta, texto, botones):
    """Subida multipart sin dependencias externas."""
    limite = "----mvn" + str(int(time.time()))
    partes = []
    for k, v in (("chat_id", str(config.TELEGRAM_CHAT_ID)), ("caption", texto[:1000]),
                 ("supports_streaming", "true"), ("width", "1080"), ("height", "1920"),
                 ("reply_markup", json.dumps({"inline_keyboard": botones}))):
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    with open(ruta, "rb") as f:
        video = f.read()
    partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="video"; filename="reel.mp4"\r\n'
                  f"Content-Type: video/mp4\r\n\r\n".encode() + video + b"\r\n")
    partes.append(f"--{limite}--\r\n".encode())
    req = urllib.request.Request(f"{API}/sendVideo", data=b"".join(partes),
                                 headers={"Content-Type": f"multipart/form-data; boundary={limite}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def bd_reels():
    bd = sqlite3.connect(REELS_BD)
    bd.execute("""CREATE TABLE IF NOT EXISTS reels(id INTEGER PRIMARY KEY, creado REAL, mundo TEXT, dia INT, ruta TEXT,
                  guion TEXT, texto TEXT, estado TEXT, instruccion TEXT, version INT DEFAULT 1)""")
    return bd


def bd_mundo():
    mundo = (config.RAIZ / ".mundo").read_text().strip() if (config.RAIZ / ".mundo").exists() else "pruebas"
    return sqlite3.connect(config.DATOS / f"{mundo}.db"), mundo


def guardar_ajuste(clave, valor):
    config.DATOS.mkdir(exist_ok=True)
    a = json.loads(config.AJUSTES.read_text()) if config.AJUSTES.exists() else {}
    a[clave] = valor
    config.AJUSTES.write_text(json.dumps(a, indent=2))


def reiniciar_motor():
    subprocess.run(["sudo", "systemctl", "restart", "miovsnuestro-motor"], check=False)


def estado():
    try:
        l = json.loads((config.DATOS / "latido.json").read_text())
        e = json.loads((config.WEB / "estado.json").read_text())
    except Exception:
        return "Todavía no hay datos del mundo."
    lineas = [f"Mundo «{e['mundo']}» · año {e['ano']} · día {e['dia']} · {l['estado']}"]
    for k in "BA":
        s = e["sociedades"][k]; m = s["metricas"]
        lineas.append(f"{s['nombre']}: {m['poblacion']} habitantes, {m['inventos']} inventos, bienestar {m['bienestar']}")
    lineas.append(f"IA: {l.get('llamadas', 0)} llamadas, {l.get('fallos', 0)} fallos, {l.get('gasto_usd_sesion', 0)} $ desde el último arranque")
    return "\n".join(lineas)


def aplicar_propuesta(clave):
    if clave == "mas_cerebros":
        guardar_ajuste("MAX_CEREBROS_POR_LADO", config.MAX_CEREBROS_POR_LADO + 10)
    elif clave == "modelo_mas_listo":
        guardar_ajuste("FRACCION_MODELO_LISTO", 0.1)
    elif clave == "acelerar":
        try:
            dia = json.loads((config.DATOS / "latido.json").read_text())["dia"]
        except Exception:
            dia = 0
        guardar_ajuste("ACELERACION", 0.5)
        guardar_ajuste("ACELERACION_HASTA_DIA", dia + 7 * config.DIAS_SIM_POR_DIA_REAL)
    elif clave == "presupuesto":
        guardar_ajuste("PRESUPUESTO_IA_EUR", config.PRESUPUESTO_MENSUAL_EUR + 10)
    reiniciar_motor()


def manejar_boton(cb):
    tipo, accion, ident = cb["data"].split(":")
    ident = int(ident)
    if tipo == "reel":
        bd = bd_reels()
        if accion == "aprobar":
            privado = not (config.DATOS / "PUBLICO").exists()
            bd.execute("UPDATE reels SET estado=? WHERE id=?", ("guardado" if privado else "aprobado", ident)); bd.commit()
            enviar("Aprobado. " + ("Queda guardado para el lanzamiento." if privado else "Pasa a la cola de publicación."))
        elif accion == "cambiar":
            guardar_ajuste("_esperando_cambio", ident)
            enviar("¿Qué quieres cambiar? Escríbemelo (por ejemplo: «más corto», «empieza por el nacimiento», «otra música»).")
    elif tipo == "prop":
        bd, _ = bd_mundo()
        fila = bd.execute("SELECT clave, titulo FROM propuestas WHERE id=?", (ident,)).fetchone()
        if not fila:
            return
        nuevo = "aprobada" if accion == "aprobar" else "rechazada"
        bd.execute("UPDATE propuestas SET estado=? WHERE id=?", (nuevo, ident)); bd.commit()
        if nuevo == "aprobada":
            aplicar_propuesta(fila[0])
            enviar(f"Propuesta aprobada y aplicada: {fila[1]}. El motor se ha reiniciado con el nuevo ajuste.")
        else:
            enviar(f"Propuesta rechazada: {fila[1]}. Todo sigue igual.")
    llamar("answerCallbackQuery", callback_query_id=cb["id"])


def manejar_texto(texto):
    a = json.loads(config.AJUSTES.read_text()) if config.AJUSTES.exists() else {}
    if a.get("_esperando_cambio") and not texto.startswith("/"):
        ident = a.pop("_esperando_cambio")
        config.AJUSTES.write_text(json.dumps(a, indent=2))
        bd = bd_reels()
        bd.execute("UPDATE reels SET estado='rehacer', instruccion=? WHERE id=?", (texto, ident)); bd.commit()
        enviar("Apuntado. Lo vuelvo a montar y te lo mando en unos minutos.")
        return
    cmd = texto.split()[0].lower()
    if cmd in ("/estado", "/start"):
        enviar(estado())
    elif cmd == "/pausa":
        (config.DATOS / "PAUSA").touch(); enviar("Mundo en pausa. Escribe /reanudar para seguir.")
    elif cmd == "/reanudar":
        (config.DATOS / "PAUSA").unlink(missing_ok=True); enviar("Mundo en marcha otra vez.")
    elif cmd == "/propuestas":
        bd, mundo = bd_mundo()
        try:
            filas = bd.execute("SELECT id, titulo, detalle, coste_actual, coste_nuevo FROM propuestas WHERE estado='pendiente' AND mundo=?", (mundo,)).fetchall()
        except sqlite3.OperationalError:
            filas = []
        if not filas:
            enviar("No hay propuestas pendientes.")
        for i, t, d, c0, c1 in filas[-5:]:
            enviar(f"{t}\n{d}\nIA: de {c0} € a {c1} € al mes.", [[{"text": "Aprobar", "callback_data": f"prop:aprobar:{i}"},
                                                               {"text": "Rechazar", "callback_data": f"prop:rechazar:{i}"}]])
    elif cmd == "/reels":
        bd = bd_reels()
        n = dict(bd.execute("SELECT estado, COUNT(*) FROM reels GROUP BY estado").fetchall())
        enviar("Reels: " + (", ".join(f"{v} {k}" for k, v in n.items()) or "ninguno todavía"))
    else:
        enviar("Comandos: /estado /pausa /reanudar /propuestas /reels")


def main():
    if not config.TELEGRAM_TOKEN:
        raise SystemExit("Falta TELEGRAM_TOKEN en .env")
    desplazamiento = 0
    while True:
        try:
            r = llamar("getUpdates", offset=desplazamiento, timeout=50)
            for u in r.get("result", []):
                desplazamiento = u["update_id"] + 1
                chat = (u.get("message") or u.get("callback_query", {}).get("message") or {}).get("chat", {}).get("id")
                if str(chat) != str(config.TELEGRAM_CHAT_ID):
                    continue  # ignora a cualquiera que no sea Oscar
                if "callback_query" in u:
                    manejar_boton(u["callback_query"])
                elif u.get("message", {}).get("text"):
                    manejar_texto(u["message"]["text"])
        except Exception as e:
            print("Error del bot:", e, flush=True)
            time.sleep(10)


if __name__ == "__main__":
    main()
