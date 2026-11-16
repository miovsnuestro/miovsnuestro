"""El prompt de decidir tiene que poder montarse con libros y con lo que te dijeron."""
import random
import unittest
from unittest.mock import patch

from sim.agente import Agente
from sim.cerebro import CerebroIA


def _agente():
    return Agente(
        id=3, nombre="Aitor", lado="A", sexo="M", edad_anos=28, x=1, y=1,
        rasgos={"sociabilidad": 0.5},
        inventario={"comida": 2}, conocimientos=set(), memoria=["Día 1: recogí raíces."],
        creencias="Hay que compartir lo que sobra.",
    )


def _ctx():
    return {
        "dia": 4, "fase": "mañana", "puede": ["recolectar", "hablar", "leer"],
        "lugar": "el valle donde nació tu gente", "sobre_otros": "No sabéis si hay más gente en el mundo.",
        "almacen": {"comida": 1}, "inventos_sociedad": set(), "descripciones": {}, "vecinos": [],
        "libros": ["El río", "La cabaña"],
        "te_dijeron": {"id": 7, "nombre": "Nerea", "frase": "ven al río", "dia": 4},
    }


class TestPromptDecidir(unittest.TestCase):
    def test_prompt_con_libros_y_te_dijeron(self):
        capturado = {}

        def falso(mensajes, modelo=None, **kwargs):
            capturado["mensajes"] = mensajes
            return '{"accion": "hablar", "objetivo": 7}'

        with patch("sim.cerebro.llamar_llm", falso):
            decision = CerebroIA(random.Random(0)).decidir(_agente(), _ctx())

        usuario = capturado["mensajes"][1]["content"]
        self.assertIn("Libros de tu gente que aún no has leído: «El río», «La cabaña».", usuario)
        self.assertIn(
            "Nerea (id 7) te ha dicho: «ven al río». "
            "Si quieres, contéstale (hablar, con su id) o sigue con lo tuyo.",
            usuario,
        )
        self.assertLess(usuario.index("Libros de tu gente"), usuario.index("te ha dicho"))
        self.assertEqual(decision["accion"], "hablar")
        self.assertEqual(decision["objetivo"], 7)


if __name__ == "__main__":
    unittest.main()
