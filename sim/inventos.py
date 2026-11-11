"""Sistema de inventos abierto.

No hay lista de descubrimientos. Un agente describe una idea con sus palabras; el árbitro
(igual para las dos sociedades) decide si es posible con lo que tienen y lo que saben, y le
asigna efectos de una lista CERRADA. El invento es libre; lo que puede hacer en el mundo
sigue unas reglas físicas iguales para todos.
"""
import json
from . import config

# Materiales que existen en el mundo. Algunos solo se pueden obtener si un invento lo habilita.
MATERIALES = ["comida", "madera", "piedra", "pescado", "carne", "pieles", "fibra", "arcilla", "metal", "carbon"]

ACTIVIDADES = ["recolectar", "talar", "picar_piedra", "pescar", "cazar", "cultivar", "criar",
               "extraer_arcilla", "extraer_metal", "extraer_carbon", "fabricar", "construir", "transportar"]
# Actividades que no se pueden hacer hasta que un invento las habilite.
REQUIEREN_INVENTO = {"pescar", "cultivar", "criar", "extraer_arcilla", "extraer_metal", "extraer_carbon", "fabricar", "transportar"}

EFECTOS = {
    "habilita": "permite una actividad nueva (objetivo = actividad)",
    "rendimiento": "multiplica lo que se obtiene en una actividad (objetivo = actividad, valor 1.1 a 3)",
    "saciedad": "la comida quita más hambre (valor 1.1 a 2)",
    "abrigo": "protege del frío (valor 0.1 a 1)",
    "conservacion": "la comida guardada se estropea menos (valor 0.1 a 1)",
    "salud": "se recupera salud más rápido (valor 0.1 a 1)",
    "ahorro_energia": "las tareas cansan menos (valor 0.1 a 0.6)",
    "alcance": "se llega más lejos a por recursos (valor 1 a 10 casillas)",
    "refugio": "sirve de vivienda para una familia",
    "defensa": "protege de robos y animales (valor 0.1 a 1)",
    "comunicacion": "las ideas se enseñan y se extienden más rápido (valor 0.1 a 1)",
    "energia": "genera fuerza o energía para fabricar (valor 1 a 10)",
}

# Categorías visuales: la web dibuja cada invento con piezas de su categoría.
CATEGORIAS = ["herramienta", "arma_caza", "ropa", "fuego_y_cocina", "recipiente", "cultivo", "animal_domestico",
              "vivienda", "taller", "almacen", "fabrica", "vehiculo_tierra", "barco", "maquina", "camino_o_puente",
              "medicina", "escritura_y_conocimiento", "moneda_o_comercio", "instrumento", "observacion_del_cielo",
              "energia", "comunicacion", "transporte_aereo", "espacial", "otro"]

REGLAS_ARBITRO = """Eres el árbitro de un experimento: decides si una idea inventada por un habitante de una sociedad primitiva
FUNCIONA en un mundo con la misma física, química y biología que la Tierra. Eres neutral y aplicas las mismas reglas a todos.

Reglas:
1. Solo puede usar materiales que tenga en su inventario y conocimientos que su sociedad ya haya inventado.
2. No se pueden saltar pasos: cada invento debe ser un paso pequeño y realista desde lo que ya existe.
   (Ej.: sin fuego no hay cerámica; sin fundir metal no hay herramientas de metal; sin ruedas ni animales no hay carros.)
3. Si la idea es vaga, imposible o se salta pasos, recházala y explica qué falta en una frase.
4. Si funciona, dale un nombre corto en español que suene natural para esa sociedad (no uses marcas ni nombres modernos
   si no corresponden), y asígnale de 1 a 3 efectos SOLO de esta lista: {efectos}.
   Actividades válidas para 'habilita' y 'rendimiento': {actividades}.
5. Elige una categoría visual de esta lista: {categorias}.
6. 'dificultad' entre 0.05 (muy fácil) y 0.95 (casi imposible): probabilidad de fallar en cada intento.
7. 'hito' = true solo si es un salto importante que merece un modelo 3D propio (primer barco, primera fábrica, primer vehículo...).

Responde SOLO con JSON:
{{"aceptado": true/false, "motivo": "...", "nombre": "...", "categoria": "...", "efectos": [{{"tipo": "...", "objetivo": "...", "valor": 1.5}}],
 "requiere": ["inventos previos en los que se apoya"], "coste": {{"material": cantidad}}, "dificultad": 0.5,
 "hito": false, "descripcion_visual": "cómo se ve, en una frase"}}"""


def _limpiar(res, conocidos):
    """Hace cumplir la lista cerrada de efectos y categorías aunque el árbitro se equivoque."""
    efectos = []
    for e in res.get("efectos", [])[:3]:
        if e.get("tipo") not in EFECTOS:
            continue
        if e["tipo"] in ("habilita", "rendimiento") and e.get("objetivo") not in ACTIVIDADES:
            continue
        v = float(e.get("valor") or 1)
        topes = {"rendimiento": (1.0, 3.0), "saciedad": (1.0, 2.0), "alcance": (1, 10), "energia": (1, 10)}
        lo, hi = topes.get(e["tipo"], (0.0, 1.0))
        efectos.append({"tipo": e["tipo"], "objetivo": e.get("objetivo"), "valor": max(lo, min(hi, v))})
    res["efectos"] = efectos
    if res.get("categoria") not in CATEGORIAS:
        res["categoria"] = "otro"
    res["coste"] = {k: int(v) for k, v in (res.get("coste") or {}).items() if k in MATERIALES and int(v) > 0}
    res["requiere"] = [r for r in res.get("requiere", []) if r in conocidos]
    res["dificultad"] = max(0.05, min(0.95, float(res.get("dificultad") or 0.5)))
    res["aceptado"] = bool(res.get("aceptado")) and bool(efectos)
    return res


def arbitrar_ia(idea, inventario, conocidos, llamar_llm):
    sistema = REGLAS_ARBITRO.format(efectos=json.dumps(EFECTOS, ensure_ascii=False),
                                    actividades=", ".join(ACTIVIDADES), categorias=", ".join(CATEGORIAS))
    usuario = (f"Idea del habitante: {idea}\nSu inventario: {inventario}\n"
               f"Inventos que ya existen en su sociedad: {', '.join(conocidos) or 'ninguno'}")
    texto = llamar_llm([{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
                       modelo=config.LLM_MODELO_LISTO, max_tokens=400, temperatura=0.3)
    return _limpiar(json.loads(texto), conocidos)


# ---------------------------------------------------------------------------------------------
# SOLO PARA PRUEBAS SIN IA: unas pocas ideas primitivas para comprobar que la maquinaria funciona.
# En el experimento real NO se usa: las ideas las escriben los agentes y las juzga el árbitro IA.
IDEAS_PRUEBA = [
    ("frotar palos secos hasta hacer fuego", [], {"madera": 2},
     {"nombre": "fuego", "categoria": "fuego_y_cocina", "efectos": [{"tipo": "saciedad", "valor": 1.4}, {"tipo": "abrigo", "valor": 0.6}]}),
    ("golpear piedras para sacarles filo", [], {"piedra": 2},
     {"nombre": "piedra afilada", "categoria": "herramienta", "efectos": [{"tipo": "rendimiento", "objetivo": "talar", "valor": 2}, {"tipo": "rendimiento", "objetivo": "cazar", "valor": 1.5}]}),
    ("atar una piedra afilada a una vara larga", ["piedra afilada"], {"madera": 1, "piedra": 1},
     {"nombre": "lanza", "categoria": "arma_caza", "efectos": [{"tipo": "rendimiento", "objetivo": "cazar", "valor": 2}, {"tipo": "habilita", "objetivo": "pescar"}]}),
    ("coser pieles con tiras de fibra", ["piedra afilada"], {"pieles": 2, "fibra": 1},
     {"nombre": "ropa de piel", "categoria": "ropa", "efectos": [{"tipo": "abrigo", "valor": 0.7}]}),
    ("apilar troncos y cubrirlos de ramas", ["piedra afilada"], {"madera": 4},
     {"nombre": "cabaña", "categoria": "vivienda", "efectos": [{"tipo": "refugio"}, {"tipo": "abrigo", "valor": 0.5}]}),
    ("enterrar semillas en tierra oscura y regarlas", ["piedra afilada"], {"comida": 3},
     {"nombre": "huerto", "categoria": "cultivo", "efectos": [{"tipo": "habilita", "objetivo": "cultivar"}]}),
    ("sacar barro de la orilla para moldearlo", ["huerto"], {"madera": 1},
     {"nombre": "barro de orilla", "categoria": "recipiente", "efectos": [{"tipo": "habilita", "objetivo": "extraer_arcilla"}]}),
    ("cocer vasijas de barro en el fuego", ["fuego", "barro de orilla"], {"arcilla": 2, "madera": 2},
     {"nombre": "vasija", "categoria": "recipiente", "efectos": [{"tipo": "conservacion", "valor": 0.7}]}),
    ("encerrar animales jóvenes y alimentarlos", ["lanza", "huerto"], {"madera": 3, "comida": 2},
     {"nombre": "corral", "categoria": "animal_domestico", "efectos": [{"tipo": "habilita", "objetivo": "criar"}], "hito": True}),
    ("calentar piedras verdes en un fuego muy fuerte", ["vasija"], {"piedra": 3, "madera": 4},
     {"nombre": "fundir", "categoria": "taller", "efectos": [{"tipo": "habilita", "objetivo": "extraer_metal"}], "hito": True}),
    ("un tronco redondo bajo una plataforma para mover cargas", ["cabaña"], {"madera": 5},
     {"nombre": "rodillo", "categoria": "vehiculo_tierra", "efectos": [{"tipo": "alcance", "valor": 4}, {"tipo": "ahorro_energia", "valor": 0.2}], "hito": True}),
    ("atar troncos con fibra para flotar y cruzar el agua", ["cabaña", "vasija"], {"madera": 6, "fibra": 2},
     {"nombre": "balsa", "categoria": "barco", "efectos": [{"tipo": "habilita", "objetivo": "transportar"}, {"tipo": "alcance", "valor": 3}], "hito": True}),
    ("marcas en la vasija para contar lo guardado", ["vasija"], {"arcilla": 1},
     {"nombre": "marcas de cuenta", "categoria": "escritura_y_conocimiento", "efectos": [{"tipo": "comunicacion", "valor": 0.4}]}),
]


def ideas_prueba_posibles(conocidos):
    return [i for i, (_, req, _, r) in enumerate(IDEAS_PRUEBA) if r["nombre"] not in conocidos and all(x in conocidos for x in req)]


def arbitrar_prueba(idea, conocidos):
    for texto, req, coste, r in IDEAS_PRUEBA:
        if texto == idea:
            if r["nombre"] in conocidos or not all(x in conocidos for x in req):
                return {"aceptado": False, "motivo": "Le falta algo previo."}
            return _limpiar({"aceptado": True, "requiere": req, "coste": coste, "dificultad": 0.8,
                             "descripcion_visual": r["nombre"], **r}, conocidos)
    return {"aceptado": False, "motivo": "No se entiende la idea."}
