"""Un habitante: cuerpo (necesidades), memoria propia y, si le toca, cerebro de IA."""
import random
from dataclasses import dataclass, field
from . import config

NOMBRES = {
    "M": ["Aitor", "Brais", "Telmo", "Uxío", "Xoán", "Martín", "Rubén", "Iago", "Hugo", "Darío",
          "Breogán", "Pablo", "Antón", "Roi", "Mateo", "Óscar", "Lois", "Xabier", "Adrián", "Ismael"],
    "F": ["Lúa", "Nerea", "Sabela", "Noa", "Iria", "Carla", "Antía", "Alba", "Uxía", "Aldara",
          "Sara", "Irene", "Lara", "Olalla", "Candela", "Mar", "Eva", "Rocío", "Xiana", "Paula"],
}


@dataclass
class Agente:
    id: int
    nombre: str
    lado: str
    sexo: str
    edad_anos: float
    x: int
    y: int
    rasgos: dict
    hambre: float = 20
    energia: float = 80
    salud: float = 100
    inventario: dict = field(default_factory=dict)
    conocimientos: set = field(default_factory=set)
    memoria: list = field(default_factory=list)
    creencias: str = ""
    relaciones: dict = field(default_factory=dict)
    pareja: int | None = None
    padres: list = field(default_factory=list)
    hijos: list = field(default_factory=list)
    refugio: bool = False
    vivo: bool = True
    con_cerebro: bool = False
    ultimo_dicho: str = ""
    ultimo_pensamiento: str = ""

    @property
    def edad(self):
        return int(self.edad_anos)

    @property
    def adulto(self):
        return self.edad >= 14

    def recordar(self, texto, maximo=40):
        self.memoria.append(texto)
        if len(self.memoria) > maximo:
            self.memoria = self.memoria[-maximo:]

    def dar(self, recurso, cantidad):
        self.inventario[recurso] = self.inventario.get(recurso, 0) + cantidad

    def quitar(self, recurso, cantidad):
        tiene = self.inventario.get(recurso, 0)
        q = min(tiene, cantidad)
        self.inventario[recurso] = tiene - q
        return q

    ALIMENTOS = ("comida", "pescado", "carne")

    def comida(self):
        return sum(self.inventario.get(k, 0) for k in self.ALIMENTOS)

    def alimento_principal(self):
        return max(self.ALIMENTOS, key=lambda k: self.inventario.get(k, 0))

    def ficha(self):
        return {
            "id": self.id, "nombre": self.nombre, "lado": self.lado, "sexo": self.sexo, "edad": self.edad,
            "hambre": round(self.hambre), "energia": round(self.energia), "salud": round(self.salud),
            "inventario": {k: v for k, v in self.inventario.items() if v}, "conocimientos": sorted(self.conocimientos),
            "pareja": self.pareja, "hijos": self.hijos, "refugio": self.refugio, "cerebro": self.con_cerebro,
            "dice": self.ultimo_dicho, "piensa": self.ultimo_pensamiento, "creencias": self.creencias, "x": self.x, "y": self.y,
        }


def crear(id_, lado, x, y, rnd, sexo=None, edad_anos=None, padres=None):
    sexo = sexo or rnd.choice("MF")
    nombre = rnd.choice(NOMBRES[sexo])
    rasgos = {k: round(rnd.random(), 2) for k in ("curiosidad", "sociabilidad", "laboriosidad", "generosidad")}
    a = Agente(id_, nombre, lado, sexo, edad_anos if edad_anos is not None else float(rnd.randint(18, 35)),
               x, y, rasgos, padres=padres or [])
    return a
