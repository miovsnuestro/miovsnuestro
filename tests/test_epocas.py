"""Las épocas se suben de una en una y el árbitro no puede poner una categoría avanzada sin que se vea en la descripción."""
from sim.simulacion import Simulacion
from sim.inventos import _limpiar


class _Falsa:
    def __init__(self, cats, habil=()):
        self.inventos = {"A": {f"i{k}": {"categoria": c, "efectos": []} for k, c in enumerate(cats)}, "B": {}}
        if habil:
            self.inventos["A"]["h"] = {"categoria": "herramienta", "efectos": [{"tipo": "habilita", "objetivo": h} for h in habil]}


def ep(cats, habil=()):
    return Simulacion.epoca_de(_Falsa(cats, habil), "A")


def test_no_se_saltan_epocas():
    # El caso real del 20-nov: aldeas + un solo «transporte_aereo» llevaba directamente a «moderna».
    assert ep(["cultivo", "transporte_aereo"]) == "aldeas"
    assert ep(["espacial"]) == "prehistoria"
    assert ep(["fabrica"]) == "prehistoria"


def test_epocas_en_orden():
    assert ep([]) == "prehistoria"
    assert ep(["cultivo"]) == "aldeas"
    assert ep(["cultivo", "moneda_o_comercio"]) == "metal"
    assert ep(["animal_domestico"], habil=["extraer_metal"]) == "metal"
    assert ep(["cultivo", "escritura_y_conocimiento", "maquina"]) == "industrial"
    assert ep(["cultivo", "escritura_y_conocimiento", "maquina", "comunicacion"]) == "moderna"
    assert ep(["cultivo", "escritura_y_conocimiento", "maquina", "comunicacion", "espacial"]) == "espacial"


def _arb(categoria, nombre, desc):
    return _limpiar({"aceptado": True, "nombre": nombre, "descripcion_visual": desc, "categoria": categoria,
                     "efectos": [{"tipo": "rendimiento", "objetivo": "fabricar", "valor": 1.2}]}, [])


def test_categoria_avanzada_sin_pruebas_pasa_a_otro():
    r = _arb("transporte_aereo", "vasija grande atada al tronco arrastrado",
             "Una vasija grande de barro atada con tiras de fibra a un tronco que se arrastra.")
    assert r["categoria"] == "otro"


def test_categoria_avanzada_con_pruebas_se_mantiene():
    assert _arb("transporte_aereo", "bolsa de piel que sube con aire caliente", "Un globo de piel que se eleva sobre el fuego.")["categoria"] == "transporte_aereo"
    assert _arb("cultivo", "surco para semillas", "Tierra removida en filas.")["categoria"] == "cultivo"
