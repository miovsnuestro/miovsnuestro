"""Objetos y construcciones reales: todo lo que inventan se puede fabricar o construir y se ve en el mundo.

- FABRICAR: con un invento de tipo «portátil» (herramienta, arma, ropa, recipiente, instrumento…), el habitante
  hace un objeto concreto y elige cómo lo quiere (qué es, color, material). Es suyo o de quien se lo dé.
- CONSTRUIR: con un invento de tipo «fijo» (fuego, vivienda, taller, almacén, corral, campo, camino, barco…),
  levanta una construcción en su sitio. Si hacen 5 hogueras, hay 5 hogueras.
- Los efectos de juego siguen saliendo de saber el invento (no cambian las reglas); los objetos y
  construcciones dan presencia visual, se pueden regalar y cuentan para la historia.
- Si algo no tiene modelo en el catálogo visual, entra en la cola de modelos y se avisa por Telegram para
  generarlo (por ejemplo con Higgsfield). Un modelo nuevo vale para las dos sociedades.
Todo es igual para los dos lados.
"""
import json
import re
import unicodedata
from . import config

# Categorías de invento → qué se hace con ellas
CAT_OBJETO = {"herramienta", "arma_caza", "ropa", "recipiente", "instrumento", "medicina",
              "escritura_y_conocimiento", "moneda_o_comercio"}
CAT_ESTRUCTURA = {
    "fuego_y_cocina": "hoguera", "vivienda": "casa", "taller": "taller", "almacen": "almacen", "fabrica": "fabrica",
    "camino_o_puente": "camino", "barco": "barco", "vehiculo_tierra": "carro", "cultivo": "campo",
    "animal_domestico": "corral", "observacion_del_cielo": "observatorio", "energia": "molino",
    "comunicacion": "torre", "maquina": "maquina", "transporte_aereo": "globo", "espacial": "cohete",
    "moneda_o_comercio": "mercado", "medicina": "enfermeria", "escritura_y_conocimiento": "escuela", "otro": "monumento",
}
# Lo que el catálogo visual ya sabe dibujar (el visor tiene el mismo listado). Lo demás pide modelo.
CATALOGO_OBJETOS = {
    "herramienta": ["hacha", "pico", "pala", "martillo", "cuchillo", "azada", "hoz", "sierra", "piedra afilada", "herramienta"],
    "arma_caza": ["lanza", "arco", "honda", "maza", "escudo", "arma"],
    "ropa": ["tunica", "camisa", "camiseta", "capa", "abrigo", "sombrero", "gorro", "falda", "pantalon", "botas", "ropa"],
    "recipiente": ["cesta", "vasija", "cuenco", "odre", "jarra", "saco", "recipiente"],
    "instrumento": ["tambor", "flauta", "instrumento"],
    "medicina": ["venda", "remedio", "medicina"],
    "escritura_y_conocimiento": ["tablilla", "libro", "pergamino", "escritura"],
    "moneda_o_comercio": ["moneda", "concha", "balanza", "moneda"],
}
CATALOGO_ESTRUCTURAS = set(CAT_ESTRUCTURA.values()) | {"horno", "puente", "pozo", "muralla", "granero"}
COLORES = {"rojo": "#C0392B", "roja": "#C0392B", "azul": "#2E6DB4", "amarillo": "#E5B92E", "amarilla": "#E5B92E",
           "verde": "#3E8E41", "blanco": "#EDEAE2", "blanca": "#EDEAE2", "negro": "#2A2A2A", "negra": "#2A2A2A",
           "marron": "#7A5232", "gris": "#8A8A8A", "naranja": "#E07B24", "morado": "#7D4FA0", "morada": "#7D4FA0",
           "rosa": "#E58FA8", "violeta": "#7D4FA0", "beige": "#D8C7A0", "ocre": "#C8963E", "granate": "#7B2433"}
MATERIAL_COLOR = {"piel": "#9A6B42", "pieles": "#9A6B42", "lino": "#E3D9C2", "lana": "#D9CDB8", "fibra": "#B9A47A",
                  "madera": "#8A6038", "piedra": "#8E8A80", "hueso": "#E6DDC8", "arcilla": "#B5653A", "barro": "#9A6440",
                  "metal": "#9AA3A8", "cobre": "#B87333", "bronce": "#B08D57", "hierro": "#6E7377", "oro": "#D4AF37"}
COSTE_OBJETO = {"herramienta": {"madera": 1, "piedra": 1}, "arma_caza": {"madera": 1, "piedra": 1},
                "ropa": {"pieles": 1}, "recipiente": {"arcilla": 1}, "instrumento": {"madera": 1},
                "medicina": {"fibra": 1}, "escritura_y_conocimiento": {"arcilla": 1}, "moneda_o_comercio": {"piedra": 1}}
COSTE_ESTRUCTURA = {"hoguera": {"madera": 2}, "casa": {"madera": 4}, "taller": {"madera": 4, "piedra": 2},
                    "almacen": {"madera": 5}, "fabrica": {"madera": 6, "piedra": 6}, "camino": {"piedra": 3},
                    "barco": {"madera": 6}, "carro": {"madera": 4}, "campo": {}, "corral": {"madera": 4},
                    "observatorio": {"piedra": 5}, "molino": {"madera": 5, "piedra": 3}, "torre": {"piedra": 6},
                    "maquina": {"madera": 4, "metal": 2}, "globo": {"fibra": 6, "madera": 2}, "cohete": {"metal": 10},
                    "mercado": {"madera": 5}, "enfermeria": {"madera": 4}, "escuela": {"madera": 5}, "monumento": {"piedra": 5}}
MAX_OBJETOS = 10
MAX_ESTRUCTURAS = 600


def claves_modelo():
    """Lista cerrada que ve el árbitro (nunca los habitantes): objeto:<tipo> o estructura:<tipo>."""
    claves = [f"objeto:{t}" for ts in CATALOGO_OBJETOS.values() for t in ts]
    return sorted(set(claves)) + sorted(f"estructura:{t}" for t in CATALOGO_ESTRUCTURAS)


def modelo_valido(modelo, categoria, nombre="", desc=""):
    """Hace cumplir la lista cerrada. Si el árbitro no eligió bien, se deduce de la categoría y la descripción."""
    m = (modelo or "").strip().lower()
    if m in claves_modelo():
        return m
    if categoria in CAT_OBJETO:
        return "objeto:" + tipo_de(f"{nombre} {desc}", categoria) if tipo_de(f"{nombre} {desc}", categoria) in CATALOGO_OBJETOS[categoria] \
            else ("nuevo" if m == "nuevo" else "objeto:" + CATALOGO_OBJETOS[categoria][-1])
    if categoria in CAT_ESTRUCTURA:
        return "nuevo" if m == "nuevo" else "estructura:" + CAT_ESTRUCTURA[categoria]
    return "nuevo" if m == "nuevo" else "estructura:monumento"


def modelo_de(info):
    """Modelo de un invento ya registrado (los antiguos sin modelo se deducen igual que arriba)."""
    return info.get("modelo") or modelo_valido("", info.get("categoria"), info.get("nombre", ""), info.get("descripcion_visual", ""))


def slug(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", "", t).strip()


def tipo_de(texto, categoria):
    """La palabra clave del objeto: «una camiseta amarilla de lino» → camiseta."""
    s = slug(texto)
    for k in CATALOGO_OBJETOS.get(categoria, []):
        if re.search(r"\b" + re.escape(k) + r"s?\b", s):
            return k
    palabras = [p for p in s.split() if p not in ("un", "una", "el", "la", "de", "del", "con", "mi", "su", "para", "los", "las")]
    return palabras[0] if palabras else categoria


def color_de(d, texto):
    s = slug((d.get("color") or "") + " " + (texto or ""))
    for nombre, hexa in COLORES.items():
        if re.search(r"\b" + nombre + r"\b", s):
            return hexa
    return None


def material_de(d, texto):
    s = slug((d.get("material") or "") + " " + (texto or ""))
    for nombre in MATERIAL_COLOR:
        if re.search(r"\b" + nombre + r"\b", s):
            return nombre
    return None


def modelos_disponibles():
    claves = set()
    for nombre in ("indice.json", "subidos.json"):  # subidos.json lo escribe el bot cuando Oscar manda un .glb
        try:
            claves |= set(json.loads((config.WEB / "modelos" / nombre).read_text()).keys())
        except Exception:
            pass
    return claves


class Fabricacion:
    """Se guarda dentro de la simulación (pickle). Todo lo de objetos y construcciones vive aquí."""

    def __init__(self):
        self.estructuras = []
        self.siguiente = 1
        self.primeros = {"A": set(), "B": set()}  # tipos ya hechos por cada sociedad (para los sucesos)
        self.campos = {}                          # (x, y) -> lado

    # ---------- qué puede hacer cada uno ----------
    @staticmethod
    def inventos_de(sim, a, cats):
        reg = sim.inventos[a.lado]
        return [n for n in sorted(a.conocimientos) if reg.get(n, {}).get("categoria") in cats]

    def puede_fabricar(self, sim, a):
        return self.inventos_de(sim, a, CAT_OBJETO)

    def puede_construir(self, sim, a):
        return self.inventos_de(sim, a, set(CAT_ESTRUCTURA) - {"vivienda"})

    # ---------- fabricar ----------
    def fabricar(self, sim, a, d, fase, invento=None, gratis=False):
        """Solo se fabrica lo que la sociedad YA descubrió y este habitante sabe hacer; cuesta material.
        Con gratis=True es la primera pieza, la del propio descubrimiento (el material ya se gastó al inventarlo)."""
        opciones = [invento] if invento else self.puede_fabricar(sim, a)
        if not opciones:
            return
        pedido = (d.get("recurso") or "").strip().lower()
        invento = next((n for n in opciones if n.lower() == pedido), None) or sim.rnd.choice(opciones)
        info = sim.inventos[a.lado][invento]
        cat = info.get("categoria")
        texto = d.get("objeto") or invento
        coste = {k: v for k, v in (info.get("coste") or COSTE_OBJETO.get(cat, {})).items()}
        if cat == "ropa" and a.inventario.get("pieles", 0) < 1 and a.inventario.get("fibra", 0) >= 2:
            coste = {"fibra": 2}
        if gratis:
            coste = {}
        falta = [k for k, v in coste.items() if a.inventario.get(k, 0) < v]
        if falta:
            a.recordar(f"Día {sim.dia}: quise hacer {texto}, pero me falta {', '.join(falta)}.")
            return
        for k, v in coste.items():
            a.quitar(k, v)
        modelo = modelo_de(info)
        tipo = modelo.split(":", 1)[1] if ":" in modelo else slug(invento) or cat
        material = material_de(d, texto)
        obj = {"id": self.siguiente, "tipo": tipo, "categoria": cat, "invento": invento, "modelo": modelo, "nombre": str(texto)[:40],
               "color": color_de(d, texto) or (MATERIAL_COLOR.get(material) if material else None), "material": material,
               "autor": a.id, "lado": a.lado, "dia": sim.dia}
        self.siguiente += 1
        destino = a
        otro = sim.agentes.get(d.get("objetivo")) if isinstance(d.get("objetivo"), int) else None
        if otro and otro.vivo and otro.id != a.id and (otro.lado == a.lado or sim.contacto):
            destino = otro
        self._dar(destino, obj)
        para = "" if destino is a else f" para {destino.nombre}"
        a.recordar(f"Día {sim.dia}: hice {texto}{para}.")
        if destino is not a:
            destino.recordar(f"Día {sim.dia}: {a.nombre} me hizo {texto}.")
            destino.relaciones[a.id] = destino.relaciones.get(a.id, 0) + 8
        clave = "objeto:" + tipo
        nuevo = clave not in self.primeros[a.lado]
        self.primeros[a.lado].add(clave)
        sim.suceso(fase, a, "objeto_nuevo" if nuevo else "fabrica",
                   f"{a.nombre} {'fabrica por primera vez' if nuevo else 'fabrica'} {texto}{para}.")
        if modelo == "nuevo":
            self._quizas_pedir_modelo(sim, "objeto", tipo, cat, obj, a)

    def primera_pieza(self, sim, a, invento, fase):
        """Al descubrir algo, lo primero que existe es la pieza del inventor (la primera hoguera, la primera piedra con mango)."""
        cat = sim.inventos[a.lado].get(invento, {}).get("categoria")
        if cat in CAT_OBJETO:
            self.fabricar(sim, a, {}, fase, invento=invento, gratis=True)
        elif cat in CAT_ESTRUCTURA and cat != "vivienda":
            self.construir(sim, a, {}, fase, invento=invento, gratis=True)

    @staticmethod
    def _dar(agente, obj):
        if not hasattr(agente, "objetos"):
            agente.objetos = []
        agente.objetos.append(obj)
        if len(agente.objetos) > MAX_OBJETOS:
            agente.objetos.pop(0)  # lo más viejo se gasta y se pierde

    def regalar_objeto(self, sim, a, otro, nombre, fase):
        objs = getattr(a, "objetos", [])
        n = slug(nombre)
        obj = next((o for o in objs if n and (n in slug(o["nombre"]) or n == o["tipo"])), None)
        if not obj:
            return False
        objs.remove(obj)
        self._dar(otro, obj)
        otro.recordar(f"Día {sim.dia}: {a.nombre} me dio {obj['nombre']}.")
        otro.relaciones[a.id] = otro.relaciones.get(a.id, 0) + 8
        sim.suceso(fase, a, "regalo", f"{a.nombre} da {obj['nombre']} a {otro.nombre}.")
        return True

    # ---------- construir ----------
    def construir(self, sim, a, d, fase, invento=None, gratis=False):
        opciones = [invento] if invento else self.puede_construir(sim, a)
        if not opciones:
            return
        pedido = (d.get("recurso") or "").strip().lower()
        invento = next((n for n in opciones if n.lower() == pedido), None) or sim.rnd.choice(opciones)
        info = sim.inventos[a.lado][invento]
        cat = info.get("categoria")
        modelo = modelo_de(info)
        tipo = modelo.split(":", 1)[1] if modelo.startswith("estructura:") else (slug(invento) if modelo == "nuevo" else CAT_ESTRUCTURA.get(cat, "monumento"))
        coste = {} if gratis else dict(COSTE_ESTRUCTURA.get(tipo, COSTE_ESTRUCTURA.get(CAT_ESTRUCTURA.get(cat, "monumento"), {"madera": 4})))
        falta = [k for k, v in coste.items() if a.inventario.get(k, 0) < v]
        if falta:
            a.recordar(f"Día {sim.dia}: quise construir {invento}, pero me falta {', '.join(falta)}.")
            return
        dueno = "comun" if str(d.get("para") or d.get("dueno") or "").lower() in ("comun", "común", "todos", "almacen") else a.id
        if not gratis and tipo not in ("camino", "campo"):
            # Si ya tiene uno igual al lado, el trabajo va a cuidarlo (avivar el fuego, reparar el corral): no aparece otro.
            igual = next((e for e in self.estructuras if e["tipo"] == tipo and e["lado"] == a.lado and e["dueno"] == dueno
                          and abs(e["x"] - a.x) + abs(e["y"] - a.y) <= 2), None)
            if igual:
                for k, v in coste.items():
                    a.quitar(k, (v + 1) // 2)
                a.recordar(f"Día {sim.dia}: cuidé {igual['nombre']}, que ya teníamos aquí.")
                return
        sitio = self._sitio(sim, a, tipo)
        if not sitio:
            a.recordar(f"Día {sim.dia}: no encontré sitio para {invento}.")
            return
        for k, v in coste.items():
            a.quitar(k, v)
        # Un fuego o un carro no se acumulan sin fin: el viejo se apaga o se deshace cuando hacen otro.
        propios = [e for e in self.estructuras if e["tipo"] == tipo and e["lado"] == a.lado and e["dueno"] == dueno]
        if tipo in ("hoguera", "carro", "barco", "globo") and len(propios) >= (1 if tipo != "hoguera" or dueno != "comun" else 3):
            self.estructuras.remove(propios[0])
        comun = dueno == "comun"
        e = {"id": self.siguiente, "tipo": tipo, "categoria": cat, "invento": invento, "modelo": modelo, "x": sitio[0], "y": sitio[1],
             "lado": a.lado, "autor": a.id, "dueno": "comun" if comun else a.id, "dia": sim.dia,
             "color": color_de(d, d.get("objeto") or ""), "nombre": str(d.get("objeto") or invento)[:40]}
        self.siguiente += 1
        self.estructuras.append(e)
        if len(self.estructuras) > MAX_ESTRUCTURAS:
            self.estructuras.pop(0)
        if tipo == "campo":
            self.campos[sitio] = a.lado
        a.recordar(f"Día {sim.dia}: construí {e['nombre']}{' para todos' if comun else ''}.")
        clave = "estructura:" + tipo
        nuevo = clave not in self.primeros[a.lado]
        self.primeros[a.lado].add(clave)
        sim.suceso(fase, a, "construccion_nueva" if nuevo else "construccion",
                   f"{a.nombre} {'construye por primera vez' if nuevo else 'construye'} {e['nombre']}{' para todos' if comun else ''}.")
        if modelo == "nuevo":
            self._quizas_pedir_modelo(sim, "estructura", tipo, cat, e, a)

    def casa(self, sim, a):
        """Las viviendas de construir_refugio también son construcciones visibles (una por familia)."""
        sitio = getattr(a, "casa", None) or (a.x, a.y)
        # se llama como ellos llamen a su vivienda (nunca con la palabra del catálogo)
        nombre = next((n for n in sorted(a.conocimientos) if sim.inventos[a.lado].get(n, {}).get("categoria") == "vivienda"), "su vivienda")
        if any(e["tipo"] == "casa" and (e["x"], e["y"]) == tuple(sitio) for e in self.estructuras):
            return
        self.estructuras.append({"id": self.siguiente, "tipo": "casa", "categoria": "vivienda", "invento": "", "x": sitio[0],
                                 "y": sitio[1], "lado": a.lado, "autor": a.id, "dueno": a.id, "dia": sim.dia, "color": None,
                                 "nombre": nombre})
        self.siguiente += 1

    def sitio_casa(self, sim, a):
        """Dónde levanta su casa: cerca de las casas de su gente si las tiene a mano (así nace el pueblo y crece),
        dejando una casilla libre entre casa y casa; si vive lejos, donde está (y allí empieza otro pueblo)."""
        m = sim.mundo
        casas = [(e["x"], e["y"]) for e in self.estructuras if e["tipo"] == "casa" and e["lado"] == a.lado]
        cerca = [c for c in casas if abs(c[0] - a.x) + abs(c[1] - a.y) <= 10]
        cx, cy = (round(sum(c[0] for c in cerca) / len(cerca)), round(sum(c[1] for c in cerca) / len(cerca))) if cerca else (a.x, a.y)
        ocupado = {(e["x"], e["y"]) for e in self.estructuras}
        for r in range(0, 9):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    x, y = cx + dx, cy + dy
                    if not (0 <= x < m.w and 0 <= y < m.h) or m.tipo[y][x] in ("agua", "rio", "mar", "cordillera", "montana"):
                        continue
                    if m.dueno[y][x] not in (a.lado, None) or any(abs(x - ox) <= 1 and abs(y - oy) <= 1 for ox, oy in ocupado):
                        continue
                    return (x, y)
        return (a.x, a.y)

    def _sitio(self, sim, a, tipo):
        m = sim.mundo
        cerca = [(a.x + dx, a.y + dy) for r in range(0, 4) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                 if abs(dx) + abs(dy) == r]
        ocupado = {(e["x"], e["y"]) for e in self.estructuras}
        for x, y in cerca:
            if not (0 <= x < m.w and 0 <= y < m.h) or (x, y) in ocupado or m.dueno[y][x] not in (a.lado, None):
                continue
            t = m.tipo[y][x]
            if tipo == "barco":
                if t in ("agua", "rio", "mar"):
                    return (x, y)
                continue
            if tipo == "campo" and t not in ("fertil", "pradera"):
                continue
            if t in ("agua", "rio", "mar", "cordillera"):
                continue
            return (x, y)
        return None

    def cultivado(self, x, y, lado):
        self.campos[(x, y)] = lado

    # ---------- cola de modelos 3D ----------
    def _quizas_pedir_modelo(self, sim, clase, tipo, cat, item, a):
        clave = f"{clase}:{tipo}"
        if clave in modelos_disponibles():
            return
        bd = sim.bd
        bd.execute("CREATE TABLE IF NOT EXISTS modelos_pendientes(clave TEXT PRIMARY KEY, clase TEXT, tipo TEXT, categoria TEXT, "
                   "descripcion TEXT, lado TEXT, dia INT, estado TEXT)")
        if bd.execute("SELECT 1 FROM modelos_pendientes WHERE clave=?", (clave,)).fetchone():
            return
        desc = item.get("nombre") or tipo
        inv = sim.inventos[a.lado].get(item.get("invento") or "", {})
        visual = inv.get("descripcion_visual", "")
        bd.execute("INSERT INTO modelos_pendientes VALUES(?,?,?,?,?,?,?,?)", (clave, clase, tipo, cat, desc, a.lado, sim.dia, "pendiente"))
        bd.commit()
        prompt = (f"Low-poly 3D model, flat shading, simple shapes, game asset, single object on neutral background: "
                  f"{desc} ({tipo}). {visual}. Primitive {('handmade' if sim.epoca_de(a.lado) in ('prehistoria', 'aldeas') else 'crafted')} style.")
        from . import avisos
        avisos.telegram(f"🧩 Modelo 3D nuevo necesario ({clase}): «{desc}» — lo ha creado {a.nombre} ({config.NOMBRE_SOCIEDAD[a.lado]}), día {sim.dia}.\n"
                        f"Mientras tanto se ve con una pieza genérica de «{cat}». Valdrá para las dos sociedades.\n"
                        f"Clave: {clave}\nPrompt para Higgsfield: {prompt}\n"
                        f"Cuando lo tengas, mándame el .glb como archivo con «{clave}» en el pie.")

    # ---------- lo que ve la web ----------
    def publico(self):
        return {"estructuras": [{k: e.get(k) for k in ("id", "tipo", "categoria", "modelo", "x", "y", "lado", "dueno", "color", "nombre")}
                                for e in self.estructuras],
                "campos": [[x, y, l] for (x, y), l in self.campos.items()]}
