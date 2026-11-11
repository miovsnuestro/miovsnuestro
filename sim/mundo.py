"""Mundo en espejo que se va descubriendo.

Disposición (de izquierda a derecha), simétrica respecto al centro:
    [frontera de B] [valle de B] [ TIERRA DE NADIE ] [valle de A] [frontera de A]
- Cada sociedad empieza conociendo solo su valle. El resto está bajo niebla.
- Su frontera exterior es solo suya (las dos son copias en espejo).
- La tierra de nadie del centro es de quien la reclame primero. Las dos sociedades
  no saben que la otra existe hasta que se encuentran allí.
"""
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
}

# Actividad -> (terrenos donde se hace, recurso que se saca, cantidad base)
ACTIVIDAD_TERRENO = {
    "recolectar": (("pradera", "fertil"), "comida", 1),
    "talar": (("bosque",), "madera", 1),
    "picar_piedra": (("roca", "montana"), "piedra", 1),
    "pescar": (("agua",), "pescado", 2),
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

    def lado_de(self, x):
        return "B" if x < self.mitad else "A"  # A (Los del Mío) a la derecha

    def accesible(self, lado, x, y):
        """Se puede usar si está explorada y es propia o de nadie."""
        return (x, y) in self.explorado[lado] and self.dueno[y][x] in (lado, None)

    def mas_cercana(self, lado, x0, y0, tipos, recurso, alcance=99, cruzar=True):
        mejor, md = None, 10**9
        for (x, y) in self.explorado[lado]:
            if self.dueno[y][x] not in (lado, None) or (not cruzar and not self.mi_orilla(lado, x)):
                continue
            if self.tipo[y][x] in tipos and self.stock[y][x].get(recurso, 0) >= 1:
                d = abs(x - x0) + abs(y - y0)
                if d < md and d <= alcance:
                    mejor, md = (x, y), d
        return mejor

    def borde_niebla(self, lado, x0, y0, rnd, cruzar=False):
        """Una casilla sin explorar pegada a lo explorado, preferiblemente cerca."""
        exp = self.explorado[lado]
        candidatos = []
        for (x, y) in exp:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < self.w and 0 <= n[1] < self.h and n not in exp and self.dueno[n[1]][n[0]] in (lado, None) \
                        and (cruzar or self.tipo[n[1]][n[0]] != "rio"):
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
        nuevas = []
        for y in range(max(0, y0 - radio), min(self.h, y0 + radio + 1)):
            for x in range(max(0, x0 - radio), min(self.w, x0 + radio + 1)):
                if not cruzar and not self.mi_orilla(lado, x):
                    continue
                if abs(x - x0) + abs(y - y0) <= radio and (x, y) not in self.explorado[lado]:
                    self.explorado[lado].add((x, y))
                    nuevas.append((x, y))
        return nuevas

    def reclamar(self, lado, x0, y0, radio=1):
        hechas = 0
        for y in range(max(0, y0 - radio), min(self.h, y0 + radio + 1)):
            for x in range(max(0, x0 - radio), min(self.w, x0 + radio + 1)):
                if self.zona[y][x] == "nadie" and self.dueno[y][x] is None and (x, y) in self.explorado[lado]:
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
                                          if self.zona[y][x] == "nadie" and self.dueno[y][x] == lado)}
