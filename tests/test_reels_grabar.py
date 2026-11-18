"""La grabación de reels no debe perder el reel entero porque una escena tarde en cargar una vez."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from reels import fabrica


class _Pagina:
    def __init__(self, falla):
        self.falla, self.cerrada, self.manejadores = falla, False, {}

    def on(self, evento, f):
        self.manejadores[evento] = f

    def set_default_timeout(self, ms):
        pass

    def goto(self, url, timeout=None):
        self.url = url

    def wait_for_function(self, expr, timeout=None):
        if self.falla:
            self.manejadores["pageerror"]("ReferenceError: algo no existe")
            raise TimeoutError("Page.wait_for_function: Timeout exceeded.")

    def evaluate(self, js):
        pass

    def screenshot(self, **kw):
        return b"jpeg"

    def close(self):
        self.cerrada = True


class _Navegador:
    def __init__(self, fallos):
        self.fallos, self.paginas = list(fallos), []

    def new_page(self, **kw):
        pg = _Pagina(self.fallos.pop(0) if self.fallos else False)
        self.paginas.append(pg)
        return pg

    def is_connected(self):
        return True

    def close(self):
        pass


def _con_playwright(nav):
    p = MagicMock()
    p.chromium.launch.return_value = nav
    ctx = MagicMock()
    ctx.__enter__.return_value = p
    mod = types.ModuleType("playwright.sync_api")
    mod.sync_playwright = lambda: ctx
    return patch.dict(sys.modules, {"playwright": types.ModuleType("playwright"), "playwright.sync_api": mod})


def _ffmpeg():
    ff = MagicMock()
    ff.wait.return_value = 0
    return patch.object(fabrica.subprocess, "Popen", return_value=ff)


ESCENAS = [{"lado": "C", "plano": "marcador", "dur": 0.1}, {"lado": "B", "plano": "aldea", "dur": 0.1}]


class TestGrabar(unittest.TestCase):
    def test_reintenta_una_escena_que_no_carga(self):
        nav = _Navegador([False, True])  # la 2.ª escena falla la primera vez y luego carga
        with _con_playwright(nav), _ffmpeg(), tempfile.TemporaryDirectory() as tmp:
            clips = fabrica.grabar([dict(e) for e in ESCENAS], "Titular", Path(tmp))
        self.assertEqual(len(clips), 2)
        self.assertEqual(len(nav.paginas), 3)
        self.assertTrue(all(pg.cerrada for pg in nav.paginas))

    def test_si_falla_siempre_avisa_con_lo_que_dijo_la_pagina(self):
        nav = _Navegador([False, True, True])
        with _con_playwright(nav), _ffmpeg(), tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError) as cm:
                fabrica.grabar([dict(e) for e in ESCENAS], "Titular", Path(tmp))
        self.assertIn("ReferenceError", str(cm.exception))
        self.assertTrue(all(pg.cerrada for pg in nav.paginas))

    def test_titular_solo_en_la_primera(self):
        self.assertIn("titular", fabrica._params_escena(dict(ESCENAS[0]), 0, "T"))
        self.assertNotIn("titular", fabrica._params_escena(dict(ESCENAS[1]), 1, "T"))
        self.assertEqual(fabrica._params_escena(dict(ESCENAS[0]), 0, "T")["sombras"], "0")  # marcador va sin sombras


if __name__ == "__main__":
    unittest.main()
