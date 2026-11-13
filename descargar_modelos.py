"""Descarga los modelos 3D de web/modelos/tripo.json y los pone en el visor (web/modelos/subidos/ + subidos.json).

Uso (como el usuario mvn, desde la carpeta del proyecto):  .venv/bin/python descargar_modelos.py
- Solo pone en el visor los que tienen "usar": true. Los demás se descargan igual (para tenerlos guardados).
- Si hay Node (npx), los aligera para el móvil: texturas WebP de 1024 px y geometría cuantizada.
- No toca el mundo ni reinicia nada: la web los usa en cuanto se recarga la página.
"""
import json, re, shutil, subprocess, sys, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
WEB = RAIZ / "web" / "modelos"
CARPETA = WEB / "subidos"


def aligerar(ruta):
    if not shutil.which("npx"):
        return "sin Node: se queda tal cual"
    tmp = ruta.with_suffix(".opt.glb")
    r = subprocess.run(["npx", "--yes", "@gltf-transform/cli@4", "optimize", str(ruta), str(tmp), "--compress", "quantize",
                        "--texture-compress", "webp", "--texture-size", "1024", "--simplify", "false"],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not tmp.exists() or tmp.read_bytes()[:4] != b"glTF":
        tmp.unlink(missing_ok=True)
        return "no se pudo aligerar (" + (r.stderr.strip().splitlines() or ["?"])[-1][:120] + "): se queda tal cual"
    antes = ruta.stat().st_size
    tmp.replace(ruta)
    return f"aligerado de {antes / 1e6:.1f} MB a {ruta.stat().st_size / 1e6:.1f} MB"


def main():
    lista = json.loads((WEB / "tripo.json").read_text(encoding="utf-8"))["modelos"]
    CARPETA.mkdir(parents=True, exist_ok=True)
    indice_ruta = WEB / "subidos.json"
    indice = json.loads(indice_ruta.read_text()) if indice_ruta.exists() else {}
    for m in lista:
        nombre = re.sub(r"[^a-z0-9]+", "_", m["clave"].lower()).strip("_") + ".glb"
        ruta = CARPETA / nombre
        if not ruta.exists():
            with urllib.request.urlopen(m["url"], timeout=180) as r:
                datos = r.read()
            if datos[:4] != b"glTF":
                print(f"✗ {m['nombre']}: lo descargado no es un .glb")
                continue
            ruta.write_bytes(datos)
            print(f"↓ {m['nombre']}: {len(datos) / 1e6:.1f} MB · {aligerar(ruta)}")
        else:
            print(f"= {m['nombre']}: ya estaba")
        if m.get("usar"):
            indice[m["clave"]] = "subidos/" + nombre
    indice_ruta.write_text(json.dumps(indice, indent=1, ensure_ascii=False))
    print(f"\nEn el visor: {', '.join(k for k in indice)}")


if __name__ == "__main__":
    sys.exit(main())
