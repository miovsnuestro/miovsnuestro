"""Motor 24/7. Lo arranca systemd en el servidor y lo reinicia si se cae.

- 1 día real = 1 año simulado: avanza un día simulado cada 48 minutos (ajustable).
- Guarda el mundo tras cada día; si el servidor se reinicia, continúa donde iba.
- Escribe web/estado.json para la web y datos/latido.json para la vigilancia.
- Si existe datos/PAUSA, se detiene sin perder nada (útil para mantenimiento o desde Telegram).
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from sim import config
from sim.simulacion import Simulacion
from sim.cerebro import Gasto

MUNDO = os.getenv("MUNDO", "pruebas")            # "pruebas" u "oficial"
SEGUNDOS_POR_DIA = float(os.getenv("SEGUNDOS_POR_DIA", str(86400 / config.DIAS_SIM_POR_DIA_REAL)))
config.DATOS.mkdir(exist_ok=True)
config.WEB.mkdir(exist_ok=True)
RUTA_BD = str(config.DATOS / f"{MUNDO}.db")
RUTA_PKL = str(config.DATOS / f"{MUNDO}.pkl")


def escribir_json(ruta, datos):
    tmp = str(ruta) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    os.replace(tmp, ruta)


def main():
    usar_ia = bool(config.LLM_API_KEY) and os.getenv("SIN_IA") != "1"
    if os.path.exists(RUTA_PKL):
        sim = Simulacion.cargar(RUTA_PKL, RUTA_BD)
        print(f"Continuando el mundo '{MUNDO}' en el día {sim.dia}", flush=True)
        if usar_ia and not sim.ia:
            from sim.cerebro import CerebroIA
            sim.ia = CerebroIA(sim.rnd)
        sim.despertar()
    else:
        sim = Simulacion(MUNDO, usar_ia=usar_ia, ruta_bd=RUTA_BD)
        print(f"Mundo '{MUNDO}' creado desde cero", flush=True)
    (config.RAIZ / ".mundo").write_text(MUNDO)
    while True:
        if (config.DATOS / "PAUSA").exists():
            escribir_json(config.DATOS / "latido.json", {"hora": time.time(), "dia": sim.dia, "estado": "en pausa"})
            time.sleep(30)
            continue
        t0 = time.time()
        sim.avanzar_dia()
        sim.cronica()
        sim.guardar(RUTA_PKL)
        escribir_json(config.WEB / "estado.json", sim.estado_publico())
        escribir_json(config.DATOS / "latido.json", {
            "hora": time.time(), "fecha": datetime.now(timezone.utc).isoformat(), "dia": sim.dia, "estado": "en marcha",
            "ia": usar_ia, "llamadas": Gasto.llamadas, "fallos": Gasto.fallos, "gasto_usd_sesion": round(Gasto.dolares, 4),
            "segundos_ultimo_dia": round(time.time() - t0, 1)})
        print(f"Día {sim.dia} listo en {time.time() - t0:.1f} s", flush=True)
        time.sleep(max(0, SEGUNDOS_POR_DIA - (time.time() - t0)))


if __name__ == "__main__":
    sys.exit(main())
