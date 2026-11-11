"""Avisos para Oscar.

Cuando una sociedad consigue un gran hito (primer barco, primera fábrica, primer vehículo...),
el mundo lo dibuja provisionalmente con piezas de su categoría y deja una tarea pendiente:
generar su modelo 3D propio con IA (por ejemplo con Higgsfield). Se avisa por Telegram para
hacerlo juntos en el chat con Claude.
"""
import json
import urllib.parse
import urllib.request
from . import config


def telegram(texto):
    """Envía un mensaje por Telegram. Sin bot configurado, lo muestra por pantalla."""
    if not (config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID):
        print(f"[AVISO] {texto}")
        return False
    datos = urllib.parse.urlencode({"chat_id": config.TELEGRAM_CHAT_ID, "text": texto}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage", data=datos, timeout=20)
        return True
    except Exception as e:
        print(f"[AVISO no enviado: {e}] {texto}")
        return False


def telegram_botones(texto, botones):
    """Mensaje con botones (por ejemplo, Aprobar / Rechazar). Sin bot, lo muestra por pantalla."""
    if not (config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID):
        print(f"[AVISO] {texto} {[b['text'] for fila in botones for b in fila]}")
        return False
    import json
    datos = urllib.parse.urlencode({"chat_id": config.TELEGRAM_CHAT_ID, "text": texto,
                                    "reply_markup": json.dumps({"inline_keyboard": botones})}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage", data=datos, timeout=20)
        return True
    except Exception as e:
        print(f"[AVISO no enviado: {e}] {texto}")
        return False


def hito_visual(sim, agente, nombre, datos):
    sim.bd.execute("""CREATE TABLE IF NOT EXISTS pendientes_visuales(id INTEGER PRIMARY KEY, mundo TEXT, dia INT, lado TEXT,
                      invento TEXT, categoria TEXT, descripcion TEXT, estado TEXT DEFAULT 'pendiente')""")
    sim.bd.execute("INSERT INTO pendientes_visuales(mundo,dia,lado,invento,categoria,descripcion) VALUES(?,?,?,?,?,?)",
                   (sim.nombre, sim.dia, agente.lado, nombre, datos.get("categoria"), datos.get("descripcion_visual", "")))
    telegram(
        f"Nuevo hito en el mundo '{sim.nombre}' (día {sim.dia}): «{config.NOMBRE_SOCIEDAD[agente.lado]}» han inventado «{nombre}» "
        f"({datos.get('categoria')}), por {agente.nombre}.\n"
        f"Cómo se ve: {datos.get('descripcion_visual', '')}\n"
        "De momento se dibuja con piezas genéricas. Abre el chat con Claude para generar su modelo 3D."
    )


def pendientes(ruta_bd=None):
    """Lista los hitos que esperan su modelo 3D."""
    import sqlite3
    bd = sqlite3.connect(ruta_bd or config.RUTA_BD)
    try:
        return bd.execute("SELECT id, mundo, dia, lado, invento, categoria, descripcion FROM pendientes_visuales "
                          "WHERE estado='pendiente' ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        return []
