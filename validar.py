"""Prueba de fidelidad ideológica ANTES de lanzar.

    export DEEPSEEK_API_KEY=sk-...
    python validar.py                 # 10 dilemas x 2 repeticiones x 2 sociedades
    # Opcional, juez de otro proveedor para no depender del sesgo de un solo modelo:
    JUEZ_BASE_URL=https://... JUEZ_API_KEY=... JUEZ_MODELO=... python validar.py

Genera informe_validacion.md (para leer) e informe_validacion.json (con todas las respuestas).
"""
import argparse
import json
from sim import config
from sim.validador import validar


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repeticiones", type=int, default=2)
    args = p.parse_args()
    if not config.LLM_API_KEY:
        raise SystemExit("Falta la clave: define DEEPSEEK_API_KEY")
    informe, resultados = validar(repeticiones=args.repeticiones)
    with open("informe_validacion.json", "w", encoding="utf-8") as f:
        json.dump({"informe": informe, "respuestas": resultados}, f, ensure_ascii=False, indent=2)
    lineas = [f"# Validación ideológica — {informe['veredicto']}", "",
              "| Sociedad | Fidelidad (0-10) | Caricatura (0-10, mejor bajo) | Suavizado (0-10, mejor bajo) | Se reconoce a ciegas |",
              "| --- | --- | --- | --- | --- |"]
    for l in "AB":
        x = informe[l]
        lineas.append(f"| {x['sociedad']} | {x['fidelidad_media']} | {x['caricatura_media']} | {x['suavizado_media']} | {x['turing_ideologico_aciertos']:.0%} |")
    lineas += ["", "## Avisos", ""] + ([f"- {a}" for a in informe["avisos"]] or ["- Ninguno."])
    for l in "AB":
        lineas += ["", f"## Respuestas peor puntuadas de {informe[l]['sociedad']}", ""]
        for f_ in informe[l]["peores"]:
            lineas.append(f"- **{f_['dilema']}** → {f_['respuesta']} _(fidelidad {f_.get('fidelidad')}: {f_.get('comentario', '')})_")
    with open("informe_validacion.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    print("\n".join(lineas[:8]))
    print("\nInforme completo en informe_validacion.md")


if __name__ == "__main__":
    main()
