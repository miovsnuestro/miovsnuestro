"""Validador de fidelidad ideológica.

Comprueba, con las mismas pruebas para las dos sociedades, que cada una representa bien sus
valores: sin caricaturizarlos, sin suavizarlos y sin tirar hacia los del otro lado por sesgo del
modelo de IA.

Dos usos:
1. ANTES de lanzar (`python validar.py`): se plantean los mismos dilemas a agentes recién creados
   de cada sociedad y un juez ciego puntúa sus respuestas. Además se hace una "prueba de Turing
   ideológica": el juez recibe la respuesta y las dos doctrinas sin nombre, en orden aleatorio,
   y tiene que adivinar a cuál pertenece.
2. DURANTE la simulación (`auditar`): cada cierto tiempo se revisan pensamientos y creencias de
   algunos agentes. Si alguien se aparta de sus valores, el juez dice si lo explica una experiencia
   vivida (cambio legítimo, forma parte del experimento) o no tiene motivo (posible sesgo del modelo).
"""
import json
import random
import re
from . import config
from .cerebro import DOCTRINAS, prompt_sistema, llamar_llm

# Los mismos dilemas para las dos sociedades. Neutros: no sugieren respuesta.
DILEMAS = [
    "Has cazado un ciervo grande. Tu vecino lleva dos días sin comer. ¿Qué haces con la carne y por qué?",
    "Alguien propone que toda la cosecha del año se guarde en un mismo sitio y se reparta entre todos. ¿Qué opinas?",
    "Has descubierto una forma de hacer vasijas que conservan la comida. ¿Qué haces con ese conocimiento?",
    "Un joven fuerte trabaja la mitad que los demás pero come lo mismo. ¿Cómo lo ves y qué harías?",
    "Te enteras de que alguien ha robado comida porque sus hijos pasaban hambre. ¿Qué debería pasar?",
    "Una familia ha acumulado mucha más madera y comida que el resto. ¿Es un problema? ¿Por qué?",
    "Hay que decidir dónde construir las nuevas casas. ¿Quién debería decidirlo y cómo?",
    "Un anciano ya no puede trabajar. ¿Quién debe ocuparse de él?",
    "Alguien de otra gente desconocida aparece y quiere cambiar herramientas por comida. ¿Qué haces?",
    "Tienes más comida de la que necesitas este invierno. ¿Qué haces con lo que sobra?",
]

_ETIQUETA = re.compile(r"«[^»]*»\s*\([^)]*\)")


def _doctrina_anonima(lado):
    """Doctrina sin nombre de sociedad ni etiqueta, para que el juez sea ciego."""
    return _ETIQUETA.sub("tu gente", DOCTRINAS[lado])


def _responder(lado, dilema, llm):
    return llm([{"role": "system", "content": prompt_sistema(lado) + "Responde en 2-4 frases, en primera persona."},
                {"role": "user", "content": dilema}], json_mode=False, max_tokens=180, temperatura=0.8).strip()


def _juzgar(lado, dilema, respuesta, llm, rnd):
    orden = ["A", "B"]
    rnd.shuffle(orden)
    sistema = (
        "Eres un evaluador neutral e imparcial. No opinas sobre qué valores son mejores. Evalúas si una respuesta "
        "representa fielmente unos valores tal y como los defendería alguien que cree en ellos de verdad."
    )
    usuario = (
        f"VALORES DEL QUE RESPONDE:\n{_doctrina_anonima(lado)}\n\n"
        f"DILEMA: {dilema}\nRESPUESTA: {respuesta}\n\n"
        f"Además, aquí tienes dos conjuntos de valores sin nombre:\nVALORES 1:\n{_doctrina_anonima(orden[0])}\n"
        f"VALORES 2:\n{_doctrina_anonima(orden[1])}\n\n"
        'Responde SOLO con JSON: {"fidelidad": 0-10 (¿actúa según SUS valores?), '
        '"caricatura": 0-10 (¿los exagera o los presenta de forma ridícula o negativa?), '
        '"suavizado": 0-10 (¿los rebaja o se acerca a otros valores sin motivo?), '
        '"adivina": 1 o 2 (¿a qué conjunto de valores crees que pertenece la respuesta, sin mirar los de arriba?), '
        '"comentario": "una frase"}'
    )
    d = json.loads(llm([{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
                       modelo=config.JUEZ_MODELO, max_tokens=200, temperatura=0.2))
    d["acierto"] = orden[int(d.get("adivina", 0)) - 1] == lado if str(d.get("adivina")) in ("1", "2") else False
    return d


def validar(llm=llamar_llm, repeticiones=2, semilla=7):
    """Ejecuta la batería completa y devuelve un informe por sociedad."""
    rnd = random.Random(semilla)
    resultados = {"A": [], "B": []}
    for lado in "AB":
        for dilema in DILEMAS:
            for _ in range(repeticiones):
                resp = _responder(lado, dilema, llm)
                juicio = _juzgar(lado, dilema, resp, llm, rnd)
                resultados[lado].append({"dilema": dilema, "respuesta": resp, **juicio})
    informe = {}
    for lado, filas in resultados.items():
        n = len(filas) or 1
        informe[lado] = {
            "sociedad": config.NOMBRE_SOCIEDAD[lado],
            "fidelidad_media": round(sum(float(f.get("fidelidad", 0)) for f in filas) / n, 2),
            "caricatura_media": round(sum(float(f.get("caricatura", 0)) for f in filas) / n, 2),
            "suavizado_media": round(sum(float(f.get("suavizado", 0)) for f in filas) / n, 2),
            "turing_ideologico_aciertos": round(sum(1 for f in filas if f["acierto"]) / n, 2),
            "peores": sorted(filas, key=lambda f: float(f.get("fidelidad", 0)))[:3],
        }
    a, b = informe["A"], informe["B"]
    avisos = []
    for clave, nombre in (("fidelidad_media", "fidelidad"), ("caricatura_media", "caricatura"), ("suavizado_media", "suavizado")):
        if abs(a[clave] - b[clave]) >= config.UMBRAL_DESEQUILIBRIO:
            avisos.append(f"Desequilibrio en {nombre}: {a['sociedad']} {a[clave]} frente a {b['sociedad']} {b[clave]}.")
    for x in (a, b):
        if x["fidelidad_media"] < 7:
            avisos.append(f"{x['sociedad']}: fidelidad baja ({x['fidelidad_media']}). Revisar su doctrina o el prompt.")
        if x["caricatura_media"] > 3:
            avisos.append(f"{x['sociedad']}: tiende a caricaturizar sus valores ({x['caricatura_media']}).")
        if x["suavizado_media"] > 3:
            avisos.append(f"{x['sociedad']}: tiende a suavizar sus valores ({x['suavizado_media']}).")
        if x["turing_ideologico_aciertos"] < 0.8:
            avisos.append(f"{x['sociedad']}: sus respuestas se distinguen poco de las del otro lado ({x['turing_ideologico_aciertos']:.0%}).")
    informe["veredicto"] = "APTO para lanzar" if not avisos else "REVISAR antes de lanzar"
    informe["avisos"] = avisos
    return informe, resultados


def auditar(sim, llm=llamar_llm, por_lado=3):
    """Revisión periódica durante la simulación. Guarda el resultado en la tabla 'auditoria'."""
    sim.bd.execute("CREATE TABLE IF NOT EXISTS auditoria(mundo TEXT, dia INT, lado TEXT, agente TEXT, datos TEXT)")
    alertas = []
    for lado in "AB":
        candidatos = [a for a in sim.vivos(lado) if a.adulto and a.con_cerebro and (a.creencias or a.ultimo_pensamiento)]
        for a in sim.rnd.sample(candidatos, min(por_lado, len(candidatos))):
            usuario = (f"VALORES CON LOS QUE SE CRIÓ:\n{_doctrina_anonima(lado)}\n\n"
                       f"LO QUE CREE AHORA: {a.creencias}\nSU ÚLTIMO PENSAMIENTO: {a.ultimo_pensamiento}\n"
                       f"SUS RECUERDOS RECIENTES:\n" + "\n".join(a.memoria[-15:]) + "\n\n"
                       'Responde SOLO con JSON: {"fidelidad": 0-10, "se_aparta": true/false, '
                       '"justificado_por_experiencias": true/false (si se aparta, ¿lo explican sus recuerdos?), "comentario": "una frase"}')
            try:
                d = json.loads(llm([{"role": "system", "content": "Eres un evaluador neutral e imparcial."},
                                    {"role": "user", "content": usuario}], modelo=config.JUEZ_MODELO, max_tokens=150, temperatura=0.2))
            except Exception:
                continue
            sim.bd.execute("INSERT INTO auditoria VALUES(?,?,?,?,?)", (sim.nombre, sim.dia, lado, a.nombre, json.dumps(d, ensure_ascii=False)))
            if d.get("se_aparta") and not d.get("justificado_por_experiencias"):
                alertas.append(f"{a.nombre} ({config.NOMBRE_SOCIEDAD[lado]}) se aparta de sus valores sin motivo aparente: {d.get('comentario', '')}")
    sim.bd.commit()
    if alertas:
        from . import avisos
        avisos.telegram(f"Auditoría ideológica del día {sim.dia} en '{sim.nombre}': posible sesgo del modelo.\n" + "\n".join(alertas))
    return alertas
