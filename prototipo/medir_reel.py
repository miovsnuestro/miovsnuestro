"""Mide cuánto tarda ESTE servidor en grabar un reel con los gráficos del prototipo «nivel 2».

Uso (desde la carpeta del proyecto):  .venv/bin/python prototipo/medir_reel.py
Graba 3 escenas de 8 s (valle, poblado y de cerca) a 640x1136 y 24 fps, con el mismo navegador y los mismos
ajustes que reels/fabrica.py, y deja el vídeo en /tmp/prueba_nivel2.mp4. No toca el mundo ni la web pública.
"""
import functools, http.server, os, subprocess, sys, threading, time
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
FPS, ANCHO, ALTO, DUR = 24, 640, 1136, 8
ESCENAS = [("general", "A"), ("poblado", "B"), ("cerca", "A")]
SALIDA = Path(os.getenv("SALIDA", "/tmp/prueba_nivel2.mp4"))
CALIDAD = os.getenv("CALIDAD", "alta")  # alta | media | baja


def servidor():
    class Callado(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Callado, directory=str(CARPETA))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    from playwright.sync_api import sync_playwright
    srv = servidor()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    clips, tiempos, inicio = [], [], time.time()
    with sync_playwright() as p:
        nav = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
                                executable_path=os.getenv("CHROME") or None)
        for i, (plano, lado) in enumerate(ESCENAS):
            t0 = time.time()
            pg = nav.new_page(viewport={"width": ANCHO, "height": ALTO}, device_scale_factor=1)
            pg.goto(f"{url}?reel=1&plano={plano}&lado={lado}&dur={DUR}&calidad={CALIDAD}")
            pg.wait_for_function("window.listo === true", timeout=300000)
            carga = time.time() - t0
            ruta = f"/tmp/prueba_nivel2_{i}.mp4"
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                                   "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", ruta], stdin=subprocess.PIPE)
            for _ in range(DUR * FPS):
                pg.evaluate(f"paso({1 / FPS})")
                ff.stdin.write(pg.screenshot(type="jpeg", quality=90))
            ff.stdin.close(); ff.wait(); pg.close()
            total = time.time() - t0
            tiempos.append((plano, carga, total))
            clips.append(ruta)
            print(f"  escena {i + 1}/3 ({plano}): carga {carga:.0f} s, grabación de {DUR} s de vídeo en {total:.0f} s", flush=True)
        nav.close()
    lista = Path("/tmp/prueba_nivel2_lista.txt")
    lista.write_text("".join(f"file '{c}'\n" for c in clips))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(SALIDA)], check=True)
    seg = time.time() - inicio
    video = DUR * len(ESCENAS)
    print(f"\nCalidad {CALIDAD}. Total: {video} s de vídeo en {seg / 60:.1f} min → {seg / video:.1f} s de servidor por cada segundo de vídeo.")
    print(f"Un reel de 40 s tardaría unos {seg / video * 40 / 60:.0f} min (sin contar voz ni montaje). Vídeo: {SALIDA}")
    srv.shutdown()


if __name__ == "__main__":
    sys.exit(main())
