"""Vigilancia del servidor. Lo lanza cron cada 5 minutos.

Comprueba que el mundo avanza, que la web responde, que la IA no falla demasiado, que queda saldo en
DeepSeek, que hay espacio en disco y que la copia de seguridad diaria existe. Si algo falla, avisa por
Telegram (como mucho una vez cada hora por problema) y, si el mundo está parado, reinicia el motor.
Además escribe datos/salud.json, que es lo que revisa Claude en la revisión diaria programada.
"""
import json
import shutil
import subprocess
import time
import urllib.request
from sim import config
from sim import avisos

ESTADO = config.DATOS / "vigilante.json"
SEG_DIA = 86400 / config.DIAS_SIM_POR_DIA_REAL


def comprobar():
    problemas, datos = [], {"hora": time.time()}
    # 1. ¿Avanza el mundo?
    try:
        l = json.loads((config.DATOS / "latido.json").read_text())
        retraso = time.time() - l["hora"]
        datos["dia"], datos["retraso_min"] = l["dia"], round(retraso / 60, 1)
        if l["estado"] != "en pausa" and retraso > 2.5 * SEG_DIA:
            problemas.append(("motor_parado", f"El mundo lleva {retraso / 60:.0f} minutos sin avanzar. Reinicio el motor."))
            subprocess.run(["sudo", "systemctl", "restart", "miovsnuestro-motor"], check=False)
        if l.get("llamadas", 0) > 200 and l.get("fallos", 0) / l["llamadas"] > 0.1:
            problemas.append(("ia_fallos", f"La IA falla en el {l['fallos'] / l['llamadas']:.0%} de las llamadas."))
    except Exception:
        problemas.append(("sin_latido", "No encuentro el latido del motor."))
    # 2. ¿Responde la web?
    try:
        urllib.request.urlopen("http://127.0.0.1/estado.json", timeout=10)
        datos["web"] = "ok"
    except Exception as e:
        datos["web"] = "caída"
        problemas.append(("web", f"La web no responde: {e}"))
    # 3. Saldo de DeepSeek
    if config.LLM_API_KEY and "deepseek" in config.LLM_BASE_URL:
        try:
            req = urllib.request.Request("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {config.LLM_API_KEY}"})
            b = json.loads(urllib.request.urlopen(req, timeout=15).read())
            saldo = sum(float(i.get("total_balance", 0)) for i in b.get("balance_infos", []))
            datos["saldo_ia"] = saldo
            if saldo < 2:
                problemas.append(("saldo", f"Queda poco saldo en DeepSeek: {saldo:.2f}. Recarga para que no se pare la IA."))
        except Exception:
            pass
    # 4. Disco
    libre = shutil.disk_usage(str(config.DATOS)).free / 1e9
    datos["disco_libre_gb"] = round(libre, 1)
    if libre < 3:
        problemas.append(("disco", f"Queda poco disco: {libre:.1f} GB."))
    # 5. Copia de seguridad de hoy
    copias = sorted((config.RAIZ / "copias").glob("*.tar.gz")) if (config.RAIZ / "copias").exists() else []
    if not copias or time.time() - copias[-1].stat().st_mtime > 26 * 3600:
        problemas.append(("copia", "No hay copia de seguridad de las últimas 24 horas."))
    # 6. Servicios y reels
    for servicio in ("miovsnuestro-motor", "miovsnuestro-bot"):
        try:
            activo = subprocess.run(["systemctl", "is-active", "--quiet", servicio]).returncode == 0
        except FileNotFoundError:
            continue
        datos[servicio] = "activo" if activo else "parado"
        if not activo:
            problemas.append((servicio, f"El servicio {servicio} está parado."))
    try:
        import sqlite3
        r = sqlite3.connect(config.DATOS / "reels.db").execute("SELECT MAX(creado) FROM reels").fetchone()[0]
        datos["ultimo_reel_horas"] = round((time.time() - r) / 3600, 1) if r else None
        if r and time.time() - r > 30 * 3600:
            problemas.append(("reels", "Hace más de 30 horas que no se genera ningún reel. Mira datos/reels.log."))
    except Exception:
        pass
    datos["problemas"] = [p[1] for p in problemas]
    (config.DATOS / "salud.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2))
    # Para la vigilancia externa (UptimeRobot busca la palabra OK en https://dominio/salud.txt)
    graves = [p[1] for p in problemas if p[0] in ("motor_parado", "sin_latido", "web", "saldo", "disco", "miovsnuestro-motor")]
    (config.WEB / "salud.txt").write_text("OK\n" if not graves else "FALLO\n" + "\n".join(graves) + "\n")
    return problemas


def main():
    previo = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    for clave, texto in comprobar():
        if time.time() - previo.get(clave, 0) > 3600:
            avisos.telegram("⚠️ " + texto)
            previo[clave] = time.time()
    ESTADO.write_text(json.dumps(previo))


if __name__ == "__main__":
    main()
