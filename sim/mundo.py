"""Mundo en espejo que se va descubriendo.

Disposición (de izquierda a derecha), simétrica respecto al centro:
    [frontera de B] [valle de B] [ TIERRA DE NADIE ] [valle de A] [frontera de A]
- Cada sociedad empieza conociendo solo su valle. El resto está bajo niebla.
- Su frontera exterior es solo suya (las dos son copias en espejo).
- La tierra de nadie del centro es de quien la reclame primero. Las dos sociedades
  no saben que la otra existe hasta que se encuentran allí.
- El mundo no tiene límite: cuando una sociedad llega a un borde y tiene los inventos para seguir
  (cruzar montañas o navegar), el mapa crece por ese lado con una barrera (cordillera o mar) y una
  región nueva detrás. Todo se genera en espejo: las dos sociedades reciben exactamente lo mismo.
"""
import math
import random
from . import config

# Qué hay en cada tipo de terreno: recurso -> (máximo, regeneración por día)
TERRENO = {
    "pradera": {"comida": (2, 0.5), "fibra": (2, 0.4), "animales": (2, 0.08)},
    "bosque": {"madera": (6, 0.4), "animales": (3, 0.1), "carbon": (4, 0.2)},
    "agua": {"pescado": (4, 0.6), "arcilla": (6, 0.5)},
    "roca": {"piedra": (5, 0.1)},
    "fertil": {"comida": (3, 0.6), "fibra": (1, 0.3)},
    "montana": {"piedra": (8, 0.1), "animales": (1, 0.05)},
    "rio": {"pescado": (5, 0.6)},  # el gran río del centro: no se cruza sin barco o puente
    "cordillera": {"piedra": (4, 0.05)},  # barrera: solo se cruza con camino, vehículo o animales de carga, y abrigo
    "mar": {"pescado": (6, 0.7)},         # barrera: solo se cruza navegando de verdad
}
BARRERAS = {"rio", "cordillera", "mar"}
# Biomas de las regiones nuevas (proporción de cada terreno). Se elige uno por ampliación, igual a los dos lados.
BIOMAS = {
    "altiplano": {"pradera": .42, "roca": .2, "montana": .1, "bosque": .16, "fertil": .07, "agua": .05},
    "bosque frío": {"bosque": .5, "pradera": .26, "roca": .1, "agua": .08, "fertil": .06},
    "valle fértil": {"fertil": .3, "pradera": .34, "bosque": .2, "agua": .1, "roca": .06},
    "costa": {"pradera": .36, "fertil": .14, "bosque": .2, "roca": .12, "agua": .18},
    "estepa": {"pradera": .58, "roca": .14, "fertil": .1, "bosque": .14, "agua": .04},
}
BARRERA_ANCHO, REGION_ANCHO = 4, 26

# Actividad -> (terrenos donde se hace, recurso que se saca, cantidad base)
ACTIVIDAD_TERRENO = {
    "recolectar": (("pradera", "fertil"), "comida", 1),
    "talar": (("bosque",), "madera", 1),
    "picar_piedra": (("roca", "montana"), "piedra", 1),
    "pescar": (("agua", "mar"), "pescado", 2),
    "cultivar": (("fertil",), "comida", 3),
    "extraer_arcilla": (("agua",), "arcilla", 1),
    "extraer_metal": (("roca", "montana"), "metal", 1),
    "extraer_carbon": (("bosque",), "carbon", 1),
}


class Mundo:
    def __init__(self, semilla=config.SEMILLA):
        self.w, self.h = config.ANCHO, config.ALTO
        f, v = config.ANCHO_FRONTERA, config.ANCHO_VALLE
        self.mitad = self.w // 2
        rnd = random.Random(semilla)
        self.tipo = [["pradera"] * self.w for _ in range(self.h)]
        self.mineral = [[False] * self.w for _ in range(self.h)]
        self.zona = [[""] * self.w for _ in range(self.h)]
        # Se genera la mitad izquierda y se copia en espejo a la derecha.
        lagos = [(f + 5, 6), (rnd.randrange(2, f - 2), rnd.randrange(4, self.h - 4)),
                 (rnd.randrange(f + v + 2, self.mitad - 1), rnd.randrange(4, self.h - 4))]
        sierra_y = rnd.randrange(self.h // 4, 3 * self.h // 4)
        for y in range(self.h):
            for x in range(self.mitad):
                r = rnd.random()
                t = "bosque" if r < 0.18 else "roca" if r < 0.23 else "fertil" if r < 0.30 else "pradera"
                if x < f // 2 and abs(y - sierra_y) < 3 and rnd.random() < 0.7:
                    t = "montana"
                for (lx, ly) in lagos:
                    if (x - lx) ** 2 / 7 + (y - ly) ** 2 / 10 < 1:
                        t = "agua"
                if x >= self.mitad - config.ANCHO_RIO_MITAD:
                    t = "rio"
                m = t in ("roca", "montana") and rnd.random() < (0.35 if t == "roca" else 0.5)
                zona = "frontera" if x < f else "valle" if x < f + v else "nadie"
                for xx, lado in ((x, "B"), (self.w - 1 - x, "A")):
                    self.tipo[y][xx] = t
                    self.mineral[y][xx] = m
                    self.zona[y][xx] = zona if zona == "nadie" else f"{zona}_{lado}"
        self.stock = [[self._lleno(x, y) for x in range(self.w)] for y in range(self.h)]
        # Dueño de cada casilla: la sociedad, o None en la tierra de nadie sin reclamar.
        self.dueno = [[(z[-1] if z != "nadie" else None) for z in fila] for fila in self.zona]
        # Lo que cada sociedad ha explorado: al principio, solo su valle.
        self.explorado = {l: {(x, y) for y in range(self.h) for x in range(self.w) if self.zona[y][x] == f"valle_{l}"} for l in "AB"}
        self.almacen = {"A": {}, "B": {}}

    def _lleno(self, x, y):
        s = {k: m for k, (m, _) in TERRENO[self.tipo[y][x]].items()}
        if self.mineral[y][x]:
            s["metal"] = 3
        return s

    @staticmethod
    def pasos_de(cruzar):
        """Qué barreras se pueden atravesar. Acepta True/False (solo el río) o un conjunto de barreras."""
        if isinstance(cruzar, (set, frozenset)):
            return cruzar
        return {"rio"} if cruzar else set()

    def transitable(self, x, y, pasos):
        t = self.tipo[y][x]
        return t not in BARRERAS or t in pasos

    def reclamable(self, x, y):
        z = self.zona[y][x]
        return (z == "nadie" or z.startswith("region")) and self.tipo[y][x] not in BARRERAS

    def lado_de(self, x):
        return "B" if x < self.mitad else "A"  # A (Los del Mío) a la derecha

    def accesible(self, lado, x, y):
        """Se puede usar si está explorada y es propia o de nadie."""
        return (x, y) in self.explorado[lado] and self.dueno[y][x] in (lado, None)

    def mas_cercana(self, lado, x0, y0, tipos, recurso, alcance=99, cruzar=True):
        mejor, md = None, 10**9
        pasos = self.pasos_de(cruzar)
        for (x, y) in self.explorado[lado]:
            if self.dueno[y][x] not in (lado, None) or ("rio" not in pasos and not self.mi_orilla(lado, x)) \
                    or not self.transitable(x, y, pasos):
                continue
            if self.tipo[y][x] in tipos and self.stock[y][x].get(recurso, 0) >= 1:
                d = abs(x - x0) + abs(y - y0)
                if d < md and d <= alcance:
                    mejor, md = (x, y), d
        return mejor

    def borde_niebla(self, lado, x0, y0, rnd, cruzar=False):
        """Una casilla sin explorar pegada a lo explorado, preferiblemente cerca."""
        exp = self.explorado[lado]
        pasos = self.pasos_de(cruzar)
        candidatos = []
        for (x, y) in exp:
            if not self.transitable(x, y, pasos):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < self.w and 0 <= n[1] < self.h and n not in exp and self.dueno[n[1]][n[0]] in (lado, None) \
                        and self.transitable(n[0], n[1], pasos):
                    candidatos.append(n)
        if not candidatos:
            return None
        candidatos.sort(key=lambda c: abs(c[0] - x0) + abs(c[1] - y0) + rnd.random() * 6)
        return candidatos[0]

    def mi_orilla(self, lado, x):
        """Sin barco ni puente, solo se ve y se usa la propia orilla del gran río."""
        r = config.ANCHO_RIO_MITAD
        return x < self.mitad + r if lado == "B" else x >= self.mitad - r

    def revelar(self, lado, x0, y0, radio, cruzar=False):
        """Descubre lo que se alcanza a pie desde (x0, y0). Las barreras que no se saben cruzar se ven
        (se sabe que están ahí), pero no se ve lo que hay detrás."""
        pasos = self.pasos_de(cruzar)
        nuevas, vistos, cola = [], {(x0, y0)}, [(x0, y0)]
        while cola:
            x, y = cola.pop(0)
            if (x, y) not in self.explorado[lado] and ("rio" in pasos or self.mi_orilla(lado, x) or self.tipo[y][x] == "rio"):
                self.explorado[lado].add((x, y))
                nuevas.append((x, y))
            if not self.transitable(x, y, pasos) and (x, y) != (x0, y0):
                continue  # una barrera: se ve, pero no se pasa
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < self.w and 0 <= n[1] < self.h and n not in vistos and abs(n[0] - x0) + abs(n[1] - y0) <= radio:
                    if "rio" not in pasos and not self.mi_orilla(lado, n[0]) and self.tipo[n[1]][n[0]] != "rio":
                        continue
                    vistos.add(n)
                    cola.append(n)
        return nuevas

    def reclamar(self, lado, x0, y0, radio=1):
        hechas = 0
        for y in range(max(0, y0 - radio), min(self.h, y0 + radio + 1)):
            for x in range(max(0, x0 - radio), min(self.w, x0 + radio + 1)):
                if self.reclamable(x, y) and self.dueno[y][x] is None and (x, y) in self.explorado[lado]:
                    self.dueno[y][x] = lado
                    hechas += 1
        return hechas

    def extraer(self, x, y, recurso, cantidad):
        cogido = min(int(self.stock[y][x].get(recurso, 0)), cantidad)
        self.stock[y][x][recurso] = self.stock[y][x].get(recurso, 0) - cogido
        return cogido

    def regenerar(self):
        for y in range(self.h):
            for x in range(self.w):
                for k, (maximo, reg) in TERRENO[self.tipo[y][x]].items():
                    self.stock[y][x][k] = min(maximo, self.stock[y][x].get(k, 0) + reg)
                if self.mineral[y][x]:
                    self.stock[y][x]["metal"] = min(3, self.stock[y][x].get("metal", 0) + 0.05)

    def resumen(self, lado):
        exp = self.explorado[lado]
        return {"explorado": len(exp), "territorio": sum(1 for y in range(self.h) for x in range(self.w) if self.dueno[y][x] == lado),
                "en_tierra_de_nadie": sum(1 for y in range(self.h) for x in range(self.w)
                                          if self.dueno[y][x] == lado and self.reclamable(x, y))}

    # ---------- el mundo crece ----------
    def borde_cercano(self, lado, direccion, margen=2):
        """¿Ha llegado esta sociedad al borde del mundo por este lado?"""
        exp = self.explorado[lado]
        if direccion == "exterior":
            return any(x <= margen for x, _ in exp) if lado == "B" else any(x >= self.w - 1 - margen for x, _ in exp)
        if direccion == "sur":
            return any(y >= self.h - 1 - margen for _, y in exp)
        return any(y <= margen for _, y in exp)  # norte

    def _tipo_region(self, bioma, u, v, semilla):
        """Terreno de una casilla nueva, en manchas (ruido suave) para que no salga a cuadros."""
        def ruido(a, b, k):
            return (math.sin(a * 0.37 + semilla * 1.7 + k) * math.cos(b * 0.41 - semilla * 0.9 + 2 * k)
                    + 0.5 * math.sin(a * 0.11 + b * 0.13 + semilla + k)) / 1.5
        n = (ruido(u, v, 0) + 1) / 2
        n = (n + random.Random(f"{semilla}:{u}:{v}").random() * 0.18) / 1.18
        acum = 0
        for t, pr in BIOMAS[bioma].items():
            acum += pr
            if n <= acum:
                return t
        return "pradera"

    def ampliar(self, direccion, nivel, semilla):
        """Añade una barrera y una región nueva por un lado (en espejo). Devuelve (dx, dy, bioma):
        cuánto se desplazan las coordenadas antiguas y qué tipo de tierra ha aparecido."""
        rnd = random.Random(f"{semilla}:{direccion}:{nivel}")
        bioma = rnd.choice(sorted(BIOMAS))
        k = BARRERA_ANCHO + REGION_ANCHO
        w, h = self.w, self.h
        if direccion == "exterior":
            nw, nh, dx, dy = w + 2 * k, h, k, 0
        elif direccion == "sur":
            nw, nh, dx, dy = w, h + k, 0, 0
        else:
            nw, nh, dx, dy = w, h + k, 0, k
        nuevo = lambda v: [[v] * nw for _ in range(nh)]
        tipo, mineral, zona, dueno = nuevo("pradera"), nuevo(False), nuevo(""), nuevo(None)
        stock = [[None] * nw for _ in range(nh)]
        for y in range(h):  # lo de antes, desplazado
            for x in range(w):
                tipo[y + dy][x + dx], mineral[y + dy][x + dx] = self.tipo[y][x], self.mineral[y][x]
                zona[y + dy][x + dx], dueno[y + dy][x + dx] = self.zona[y][x], self.dueno[y][x]
                stock[y + dy][x + dx] = self.stock[y][x]
        mitad, rio = nw // 2, config.ANCHO_RIO_MITAD
        nombre_zona = f"region_{direccion}_{nivel + 1}"
        for y in range(nh):
            for x in range(mitad):  # se genera la mitad izquierda y se copia en espejo
                if stock[y][x] is not None:
                    continue
                if direccion == "exterior":
                    barrera = x >= k - BARRERA_ANCHO
                    t = "cordillera" if barrera else self._tipo_region(bioma, x, y, nivel * 7 + 1)
                elif direccion == "sur":
                    barrera = y < h + BARRERA_ANCHO
                    t = "mar" if barrera else ("rio" if x >= mitad - rio else self._tipo_region(bioma, x, y - h, nivel * 7 + 3))
                else:
                    barrera = y >= k - BARRERA_ANCHO
                    t = "cordillera" if barrera else ("rio" if x >= mitad - rio else self._tipo_region(bioma, x, y, nivel * 7 + 5))
                m = t in ("roca", "montana", "cordillera") and rnd.random() < (0.5 if bioma == "altiplano" else 0.3)
                for xx in (x, nw - 1 - x):
                    tipo[y][xx], mineral[y][xx] = t, m
                    zona[y][xx] = "barrera" if barrera else nombre_zona
                    dueno[y][xx] = None
                    stock[y][xx] = None
        self.w, self.h, self.mitad = nw, nh, mitad
        self.tipo, self.mineral, self.zona, self.dueno = tipo, mineral, zona, dueno
        for y in range(nh):
            for x in range(nw):
                if stock[y][x] is None:
                    stock[y][x] = self._lleno(x, y)
        self.stock = stock
        self.explorado = {l: {(x + dx, y + dy) for x, y in e} for l, e in self.explorado.items()}
        return dx, dy, bioma
