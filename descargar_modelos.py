"""Descarga los modelos 3D de web/modelos/tripo.json y los pone en el visor (web/modelos/subidos/ + subidos.json).

Uso (como el usuario mvn, desde la carpeta del proyecto):  .venv/bin/python descargar_modelos.py
- Solo pone en el visor los que tienen "usar": true y pesan como mucho MAX_MB (los modelos de Tripo salen de
  40-50 MB: sin aligerar no se ponen, porque el móvil tendría que bajarse cientos de MB).
- Los aligera con gltf-transform (Node): texturas WebP de 1024 px, malla simplificada y geometría cuantizada.
  Si no hay Node en el sistema, se instala uno propio en .node/ (sin root, solo para esto).
- Los ya descargados se vuelven a aligerar si aún pesan demasiado.
- No toca el mundo ni reinicia nada: la web los usa en cuanto se recarga la página.
"""
import json, os, platform, re, shutil, subprocess, sys, tarfile, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
WEB = RAIZ / "web" / "modelos"
CARPETA = WEB / "subidos"
MAX_MB = 6
NODE_PROPIO = RAIZ / ".node"
NODE_VERSION = "v20.18.1"


def npx():
    """El npx del sistema o, si no hay, uno propio en .node/ (se descarga la primera vez)."""
    propio = NODE_PROPIO / "bin" / "npx"
    if propio.exists():
        return str(propio)
    if shutil.which("npx"):
        return shutil.which("npx")
    arq = {"x86_64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine(), "x64")
    nombre = f"node-{NODE_VERSION}-linux-{arq}"
    print(f"Instalando Node {NODE_VERSION} en {NODE_PROPIO} (solo para aligerar modelos)…", flush=True)
    tar = RAIZ / f"{nombre}.tar.xz"
    urllib.request.urlretrieve(f"https://nodejs.org/dist/{NODE_VERSION}/{nombre}.tar.xz", tar)
    with tarfile.open(tar) as t:
        t.extractall(RAIZ)
    tar.unlink()
    (RAIZ / nombre).rename(NODE_PROPIO)
    return str(propio)


def aligerar(ruta):
    try:
        cmd = npx()
    except Exception as e:
        return f"no hay Node ni se pudo instalar ({e}): se queda tal cual"
    tmp = ruta.with_suffix(".opt.glb")
    entorno = {**os.environ, "PATH": str(Path(cmd).parent) + os.pathsep + os.environ.get("PATH", "")}
    r = subprocess.run([cmd, "--yes", "@gltf-transform/cli@4", "optimize", str(ruta), str(tmp), "--compress", "quantize",
                        "--texture-compress", "webp", "--texture-size", "1024",
                        "--simplify", "true", "--simplify-ratio", "0.1", "--simplify-error", "0.002"],
                       capture_output=True, text=True, timeout=900, env=entorno)
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
        elif ruta.stat().st_size > MAX_MB * 1e6:
            print(f"= {m['nombre']}: ya estaba, pero pesa {ruta.stat().st_size / 1e6:.1f} MB · {aligerar(ruta)}")
        else:
            print(f"= {m['nombre']}: ya estaba ({ruta.stat().st_size / 1e6:.1f} MB)")
        if m.get("usar") and ruta.stat().st_size <= MAX_MB * 1e6:
            indice[m["clave"]] = "subidos/" + nombre
        elif indice.get(m["clave"]) == "subidos/" + nombre:
            del indice[m["clave"]]
            print(f"  ⚠ {m['nombre']} pesa demasiado para el móvil: queda fuera del visor hasta que se aligere")
    indice_ruta.write_text(json.dumps(indice, indent=1, ensure_ascii=False))
    print(f"\nEn el visor: {', '.join(k for k in indice) or 'ninguno'}")


if __name__ == "__main__":
    sys.exit(main())
