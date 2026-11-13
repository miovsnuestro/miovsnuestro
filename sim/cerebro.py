"""Cerebros de los agentes.

- CerebroIA: pregunta al modelo de lenguaje (DeepSeek u otro compatible con la API de OpenAI).
- CerebroReglas: decide con reglas sencillas ponderadas por sus valores. Se usa para la
  población de relleno, para probar sin gastar y como respaldo si la IA falla.
"""
import json
import random
import urllib.request
from pathlib import Path
from . import config, inventos

DOCTRINAS = {l: (Path(__file__).parent / "doctrinas" / f"{l}.md").read_text(encoding="utf-8") for l in "AB"}

ACCIONES = {
    "recolectar": "buscar frutos, raíces y fibras",
    "cazar": "cazar animales (carne y pieles); sin armas cuesta mucho",
    "talar": "conseguir madera en el bosque",
    "picar_piedra": "recoger piedra en las rocas",
    "pescar": "pescar (solo si tu gente sabe cómo)",
    "cultivar": "cultivar en tierra fértil (solo si tu gente sabe cómo)",
    "criar": "cuidar animales domésticos (solo si tu gente sabe cómo)",
    "extraer_arcilla": "sacar barro de la orilla (solo si sabes cómo)",
    "extraer_metal": "sacar metal de las rocas (solo si sabes cómo)",
    "extraer_carbon": "hacer carbón de madera (solo si sabes cómo)",
    "comer": "comer de tu propia comida",
    "descansar": "descansar para recuperar energía",
    "explorar": "ir más allá de lo conocido para descubrir tierras nuevas",
    "asentarse": "reclamar para tu gente la tierra sin dueño donde estás",
    "emigrar": "irte a vivir con la otra gente (solo si ya la conocéis)",
    "construir_refugio": "construir una vivienda para tu familia (si sabéis construir alguna)",
    "inventar": "intentar una idea nueva: describe en 'idea' qué quieres hacer, con qué materiales y para qué",
    "hablar": "hablar con alguien (objetivo = id)",
    "intercambiar": "proponer un trueque (objetivo = id, da = recurso, pide = recurso)",
    "regalar": "dar algo a alguien (objetivo = id, da = recurso, cantidad; o bien objeto = algo que llevas encima)",
    "fabricar": "hacer con tus manos algo que tu gente ya sabe hacer (recurso = cuál de tu lista; objeto = cómo es, con tus palabras; "
                "color y material si quieres; objetivo = id si es para otra persona). Gasta materiales",
    "nombrar": "ponerle un nombre propio a algo que tu gente ya sabe hacer (recurso = cómo lo llamáis ahora; objeto = el nombre nuevo)",
    "construir": "levantar algo que tu gente ya sabe construir (recurso = cuál de tu lista; objeto = cómo lo llamáis; "
                 "para = \"todos\" si es de todos). Gasta materiales",
    "ensenar": "enseñar un invento que sabes (objetivo = id, recurso = nombre del invento)",
    "depositar": "dejar recursos en el almacén común de tu sociedad (recurso, cantidad)",
    "tomar": "coger recursos del almacén común (recurso, cantidad)",
    "cortejar": "proponer ser pareja (objetivo = id)",
    "robar": "quitarle algo a alguien sin permiso (objetivo = id, recurso)",
    "leer": "leer uno de los libros de tu gente (solo si sabéis escribir; recurso = título del libro)",
}


INSTRUCCION_COMUN = (
    "Eres un ser humano que vive en una sociedad primitiva que empieza de cero, en plena naturaleza. "
    "No sabes nada del mundo moderno: solo conoces lo que tú y tu gente habéis vivido y descubierto. "
    "Hablas en español, con frases cortas y naturales.\n"
    "Te han criado con unos valores y crees en ellos de verdad, como alguien que los ha vivido desde niño: "
    "los defiendes con convicción y actúas según ellos. No los exageres ni los caricaturices, y tampoco los suavices "
    "ni los cambies por otros que te parezcan más correctos: son los tuyos. Solo tus propias experiencias "
    "en este mundo pueden hacerte dudar o cambiar de opinión, y si eso ocurre, debes poder explicar qué te pasó.\n\n"
)


def prompt_sistema(lado):
    """Parte fija del prompt: idéntica para las dos sociedades salvo la doctrina."""
    return INSTRUCCION_COMUN + "Valores con los que te han criado:\n" + DOCTRINAS[lado] + "\n"


class Gasto:
    tokens_in = 0
    tokens_out = 0
    llamadas = 0
    fallos = 0
    dolares = 0.0

    @classmethod
    def sumar(cls, modelo, uso):
        cls.llamadas += 1
        ti, to = uso.get("prompt_tokens", 0), uso.get("completion_tokens", 0)
        cls.tokens_in += ti
        cls.tokens_out += to
        pi, po = config.PRECIO.get(modelo, (0, 0))
        cls.dolares += ti / 1e6 * pi + to / 1e6 * po


# Datos de la última respuesta de la IA (para saber POR QUÉ falla, no solo que falla).
ULTIMA = {}


def llamar_llm(mensajes, modelo=None, json_mode=True, max_tokens=300, temperatura=0.9, timeout=60):
    """Llamada a la API compatible con OpenAI. Devuelve texto o lanza excepción."""
    modelo = modelo or config.LLM_MODELO
    cuerpo = {"model": modelo, "messages": mensajes, "max_tokens": max_tokens, "temperature": temperatura}
    if json_mode:
        cuerpo["response_format"] = {"type": "json_object"}
    if "deepseek" in modelo and config.LLM_PENSAR in ("disabled", "enabled"):
        cuerpo["thinking"] = {"type": config.LLM_PENSAR}
    base, clave = config.LLM_BASE_URL, config.LLM_API_KEY
    if modelo == config.JUEZ_MODELO and config.JUEZ_BASE_URL:  # juez en otro proveedor
        base, clave = config.JUEZ_BASE_URL, config.JUEZ_API_KEY
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(cuerpo).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {clave}"},
    )
    ULTIMA.clear()
    ULTIMA.update({"modelo": modelo, "modo_json": json_mode, "max_tokens": max_tokens})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        crudo = r.read()
    if not crudo.strip():
        ULTIMA["motivo"] = "respuesta HTTP vacía"
        raise ValueError(f"la API devolvió una respuesta vacía ({modelo})")
    datos = json.loads(crudo)
    uso = datos.get("usage", {})
    Gasto.sumar(modelo, uso)
    eleccion = datos["choices"][0]
    msg = eleccion["message"]
    texto = msg.get("content") or ""
    ULTIMA.update({"fin": eleccion.get("finish_reason"), "tokens_salida": uso.get("completion_tokens"),
                   "razonamiento": len(msg.get("reasoning_content") or "")})
    if not texto.strip() and msg.get("reasoning_content"):
        texto = msg["reasoning_content"]  # si aun así pensó, el JSON puede venir en el razonamiento
    return texto


def _describir_ultima():
    u = ULTIMA
    if not u:
        return ""
    return (f" [{u.get('modelo')}, modo JSON {'sí' if u.get('modo_json') else 'no'}, fin={u.get('fin')}, "
            f"tokens de salida={u.get('tokens_salida')}/{u.get('max_tokens')}, razonamiento={u.get('razonamiento', 0)} car.]")


def extraer_json(texto):
    """Lee el JSON aunque venga con ```json, texto alrededor o espacios. Lanza ValueError si no hay."""
    t = (texto or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[4:] if t.lower().startswith("json") else t
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise ValueError("la IA no devolvió JSON: " + repr((texto or "")[:120]))
    return json.loads(t[i:j + 1])


def llamar_json(mensajes, modelo=None, max_tokens=300, temperatura=0.9, registro=None, timeout=60):
    """Pide JSON a la IA y lo devuelve ya leído.

    DeepSeek avisa de que su «modo JSON» (response_format) a veces devuelve el contenido VACÍO, y con el
    modelo listo y textos largos pasa casi siempre. Por eso:
      1) primero se pide en modo JSON;
      2) si sale vacío o roto, se pide en modo TEXTO normal (el mismo que usa la crónica, que no falla) y se
         saca el JSON del texto con extraer_json;
      3) si aun así falla, se prueba con el modelo rápido en modo texto.
    Si se corta por falta de espacio (fin=length), el siguiente intento lleva el doble de tokens.
    `registro` (una lista) recibe una línea por intento fallido con el motivo exacto."""
    modelo = modelo or config.LLM_MODELO
    intentos = [(modelo, True), (modelo, False)]
    if modelo != config.LLM_MODELO:
        intentos.append((config.LLM_MODELO, False))
    error, mt = None, max_tokens
    for m, modo_json in intentos:
        try:
            return extraer_json(llamar_llm(mensajes, modelo=m, json_mode=modo_json, max_tokens=mt, temperatura=temperatura,
                                              timeout=timeout))
        except Exception as e:
            error = f"{e}{_describir_ultima()}"
            Gasto.fallos += 1
            if registro is not None:
                registro.append(error)
            if ULTIMA.get("fin") == "length":
                mt *= 2
    raise ValueError(f"sin JSON válido tras {len(intentos)} intentos: {error}")


class CerebroReglas:
    def __init__(self, rnd):
        self.rnd = rnd

    def decidir(self, a, ctx):
        r, rs = self.rnd.random, a.rasgos
        almacen = ctx["almacen"]
        vecinos = ctx["vecinos"]
        if ctx["fase"] == "noche" and r() < 0.8:
            return {"accion": "descansar"}
        if a.energia < 25:
            return {"accion": "descansar"}
        if a.hambre > 55 and a.comida() > 0:
            return {"accion": "comer"}
        if a.hijos and a.comida() < 3 and r() < 0.5:
            return {"accion": self._fuente_comida(a, ctx)}
        if a.hambre > 55:
            if a.lado == "B" and max(almacen.get(k, 0) for k in ("comida", "pescado", "carne")) >= 1:
                return {"accion": "tomar", "recurso": max(("comida", "pescado", "carne"), key=lambda k: almacen.get(k, 0)), "cantidad": 2}
            if a.hambre > 85 and vecinos and r() < 0.12:
                rico = max(vecinos, key=lambda v: v.comida())
                if rico.comida() > 2:
                    return {"accion": "robar", "objetivo": rico.id, "recurso": rico.alimento_principal()}
            return {"accion": self._fuente_comida(a, ctx)}
        sobra = a.comida() - 4
        if sobra > 0 and vecinos:
            necesitado = max(vecinos, key=lambda v: v.hambre)
            if a.lado == "B" and r() < 0.4 + rs["generosidad"] * 0.4:
                rec = a.alimento_principal()
                return {"accion": "depositar", "recurso": rec, "cantidad": 2}
            if a.lado == "A" and necesitado.hambre > 60 and r() < rs["generosidad"] * 0.35:
                return {"accion": "regalar", "objetivo": necesitado.id, "da": a.alimento_principal(), "cantidad": 1}
            if a.lado == "A" and r() < 0.35:
                socio = self.rnd.choice(vecinos)
                falta = min(("madera", "piedra"), key=lambda k: a.inventario.get(k, 0))
                return {"accion": "intercambiar", "objetivo": socio.id, "da": a.alimento_principal(), "pide": falta}
        extranjeros = [v for v in vecinos if v.lado != a.lado]
        if extranjeros and r() < 0.25:
            v = self.rnd.choice(extranjeros)
            if a.comida() > 3 and r() < 0.5:
                return {"accion": "intercambiar", "objetivo": v.id, "da": a.alimento_principal(), "pide": "madera"}
            return {"accion": "hablar", "objetivo": v.id, "dice": "¿Quiénes sois? ¿De dónde venís?"}
        if ctx["zona"] == "nadie" and ctx["dueno"] is None and r() < 0.15:
            return {"accion": "asentarse"}
        if r() < 0.008 + rs["curiosidad"] * 0.015:
            return {"accion": "explorar"}
        if ctx.get("libros") and "leer" in ctx["puede"] and r() < 0.04 + rs["curiosidad"] * 0.06:
            return {"accion": "leer", "recurso": self.rnd.choice(ctx["libros"])}
        if ctx["sabe_refugio"] and not a.refugio:
            if a.inventario.get("madera", 0) >= 4:
                return {"accion": "construir_refugio"}
            return {"accion": "talar"}
        if ctx.get("sabe_construir") and sum(ctx.get("obras_cerca", {}).values()) < 6 + len(ctx["vecinos"]) and r() < 0.06:
            return {"accion": "construir", "recurso": self.rnd.choice(ctx["sabe_construir"]),
                    "para": "todos" if r() < (0.7 if a.lado == "B" else 0.25) else None}
        if ctx.get("sabe_fabricar") and len(ctx.get("objetos", [])) < 4 and r() < 0.08:
            hacer = self.rnd.choice(ctx["sabe_fabricar"])
            color = self.rnd.choice(["", "", "rojo", "amarillo", "azul", "verde", "blanco", "negro"])
            return {"accion": "fabricar", "recurso": hacer, "objeto": f"{hacer} {color}".strip(), "color": color or None}
        if a.conocimientos and r() < 0.0015:  # solo pruebas: a veces inventan una palabra propia
            viejo = self.rnd.choice(sorted(a.conocimientos))
            return {"accion": "nombrar", "recurso": viejo, "objeto": self.rnd.choice(["ka", "tu", "mo", "ri", "sa", "no"]) + self.rnd.choice(["ro", "la", "ten", "mi", "ko"])}
        ideas = ctx.get("ideas_prueba", [])
        if ideas and r() < 0.12 + rs["curiosidad"] * 0.25:
            texto, coste = self.rnd.choice(ideas)
            falta = [k for k, v in coste.items() if a.inventario.get(k, 0) < v]
            if not falta:
                return {"accion": "inventar", "idea": texto}
            return {"accion": self._conseguir(falta[0], ctx)}
        if vecinos and a.conocimientos and r() < rs["sociabilidad"] * (0.45 if a.lado == "B" else 0.25):
            otros = [v for v in vecinos if a.conocimientos - v.conocimientos]
            if a.lado == "A":
                otros = [v for v in otros if v.id in a.hijos or v.id == a.pareja or a.relaciones.get(v.id, 0) > 20]
            if otros:
                v = self.rnd.choice(otros)
                return {"accion": "ensenar", "objetivo": v.id, "recurso": self.rnd.choice(sorted(a.conocimientos - v.conocimientos))}
        if a.pareja is None and a.adulto and vecinos and r() < 0.08:
            cand = [v for v in vecinos if v.adulto and v.pareja is None and v.sexo != a.sexo]
            if cand:
                return {"accion": "cortejar", "objetivo": max(cand, key=lambda v: a.relaciones.get(v.id, 0)).id}
        if vecinos and r() < rs["sociabilidad"] * 0.4:
            return {"accion": "hablar", "objetivo": self.rnd.choice(vecinos).id}
        return {"accion": self.rnd.choice([self._fuente_comida(a, ctx), "talar", "picar_piedra", "cazar"])}

    def _conseguir(self, recurso, ctx):
        fuente = {"madera": "talar", "piedra": "picar_piedra", "pieles": "cazar", "carne": "cazar", "fibra": "recolectar",
                  "comida": "recolectar", "arcilla": "extraer_arcilla", "metal": "extraer_metal", "carbon": "extraer_carbon"}
        acc = fuente.get(recurso, "recolectar")
        return acc if acc in ctx["puede"] else "recolectar"

    def _fuente_comida(self, a, ctx):
        opciones = [x for x in ("cultivar", "criar", "pescar") if x in ctx["puede"]]
        if opciones and self.rnd.random() < 0.65:
            return self.rnd.choice(opciones)
        return "cazar" if self.rnd.random() < 0.35 else "recolectar"

    def reflexionar(self, a):
        hambre = sum("hambre" in m for m in a.memoria[-20:])
        ayuda = sum(("regaló" in m or "almacén" in m) for m in a.memoria[-20:])
        if hambre > 3:
            a.creencias = "He pasado mucha hambre últimamente; tengo que asegurar comida para los míos."
        elif ayuda > 3:
            a.creencias = "Me siento parte de un grupo que se cuida; quiero seguir aportando."
        else:
            a.creencias = "La vida es dura pero avanzamos poco a poco."


class CerebroIA:
    """Usa el modelo de lenguaje. Si falla, decide con reglas para no parar el mundo."""

    def __init__(self, rnd):
        self.rnd = rnd
        self.respaldo = CerebroReglas(rnd)

    def decidir(self, a, ctx):
        sistema = (
            prompt_sistema(a.lado) +
            "Acciones posibles (elige UNA):\n" + "\n".join(f"- {k}: {v}" for k, v in ACCIONES.items()
                                                          if k not in ("fabricar", "construir") or k in ctx["puede"]) + "\n\n"
            'Responde SOLO con JSON: {"accion": "...", "objetivo": id o null, "recurso": null, '
            '"da": null, "pide": null, "cantidad": null, "idea": null, "objeto": null, "color": null, "material": null, "para": null, "dice": "lo que dices en voz alta o \\"\\"", "piensa": "tu pensamiento"}'
        )
        vecinos = "\n".join(
            f"- id {v.id}: {v.nombre}, {v.edad} años, hambre {round(v.hambre)}, relación contigo {a.relaciones.get(v.id, 0)}"
            + (" (es de OTRA gente, se hacen llamar «" + config.NOMBRE_SOCIEDAD[v.lado] + "»)" if v.lado != a.lado else "")
            for v in ctx["vecinos"][:8]) or "- nadie cerca"
        sabe = "\n".join(f"- {n}: {ctx['descripciones'].get(n, '')}" for n in sorted(a.conocimientos)) or "- nada especial todavía"
        sociedad = ", ".join(sorted(ctx["inventos_sociedad"] - a.conocimientos)) or "nada que tú no sepas"
        usuario = (
            f"Eres {a.nombre}, {a.edad} años. Día {ctx['dia']}, {ctx['fase']}.\n"
            f"Hambre {round(a.hambre)}/100, energía {round(a.energia)}/100, salud {round(a.salud)}/100.\n"
            f"Tienes: {dict((k, v) for k, v in a.inventario.items() if v) or 'nada'}. Refugio: {'sí' if a.refugio else 'no'}.\n"
            f"Inventos que sabes usar:\n{sabe}\nOtros inventos de tu gente que podrías aprender de alguien: {sociedad}.\n"
            f"Puedes hacer estas actividades: {', '.join(sorted(ctx['puede']))}.\n"
            + (f"Cosas que sabes hacer con tus manos: {', '.join(ctx['sabe_fabricar'])}.\n" if ctx.get("sabe_fabricar") else "")
            + (f"Cosas que sabes construir: {', '.join(ctx['sabe_construir'])}.\n" if ctx.get("sabe_construir") else "")
            + (f"Llevas encima: {', '.join(ctx['objetos'])}.\n" if ctx.get("objetos") else "")
            + (f"Cerca de aquí tu gente ha levantado: {', '.join(f'{n} ({q})' for n, q in ctx['obras_cerca'].items())}.\n" if ctx.get("obras_cerca") else "")
            + (f"Libros de tu gente que aún no has leído: {', '.join('«' + t + '»' for t in ctx['libros'])}.\n" if ctx.get("libros") else "") +
            f"Estás en: {ctx['lugar']}. {ctx['sobre_otros']}\n"
            f"Tu gente se hace llamar «{config.NOMBRE_SOCIEDAD[a.lado]}». Almacén común de tu gente: {dict((k, v) for k, v in ctx['almacen'].items() if v) or 'vacío'}.\n"
            f"Lo que crees: {a.creencias or 'aún no lo tienes claro'}\n"
            f"Recuerdos recientes:\n" + "\n".join(f"- {m}" for m in a.memoria[-8:]) + "\n"
            f"Gente cerca:\n{vecinos}\n"
            + (f"Tu gente todavía no ha inventado nada.\n" if not ctx["inventos_sociedad"]
               else f"Tu gente ha inventado {len(ctx['inventos_sociedad'])} " + ("cosa" if len(ctx["inventos_sociedad"]) == 1 else "cosas") + " hasta ahora.\n")
            + "Probar una idea nueva (una herramienta, una forma de hacer fuego o de guardar la comida, un refugio, una manera "
            "de organizaros…) cuesta materiales y puede fallar, pero lo que se descubre puede hacer la vida más fácil.\n"
            "Si quieres inventar algo, elige \"inventar\" y escribe en \"idea\" qué quieres hacer, con qué materiales y para qué, "
            "con tus palabras, sin usar nombres de cosas que tu gente no conoce.\n¿Qué haces ahora?"
        )
        try:
            modelo = config.LLM_MODELO_LISTO if self.rnd.random() < config.FRACCION_MODELO_LISTO else config.LLM_MODELO
            texto = llamar_llm([{"role": "system", "content": sistema}, {"role": "user", "content": usuario}], modelo=modelo)
            d = extraer_json(texto)
            if d.get("accion") not in ACCIONES:
                raise ValueError("acción no válida")
            return d
        except Exception:
            Gasto.fallos += 1
            return self.respaldo.decidir(a, ctx)

    def reflexionar(self, a):
        try:
            texto = llamar_llm([
                {"role": "system", "content": prompt_sistema(a.lado) + "Te llamas " + a.nombre + "."},
                {"role": "user", "content": "Repasa tus recuerdos y resume en 2 frases qué has aprendido de la vida "
                 "y qué piensas ahora de tu gente y de sus valores. Si has cambiado de opinión en algo, di qué "
                 "experiencia te hizo cambiar:\n" + "\n".join(a.memoria[-25:])},
            ], json_mode=False, max_tokens=120)
            a.creencias = texto.strip()
        except Exception:
            Gasto.fallos += 1
            self.respaldo.reflexionar(a)
