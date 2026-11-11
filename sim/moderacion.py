"""Filtro de contenido antes de publicar.

Todo lo que dicen y piensan los agentes, y la crónica diaria, pasa por aquí antes de salir en la
web o en un reel. Si algo no es publicable, se sustituye por «[…]» en la versión pública, se guarda
el original para revisión y se avisa por Telegram. La simulación no se toca: solo lo que se enseña.

Dos capas:
1. Reglas rápidas (gratis): insultos graves, odio, violencia explícita, sexual, y nombres de partidos
   o políticos reales (los agentes no deberían conocerlos; si aparecen, es una fuga del modelo).
2. Opcional, IA moderadora (MODERACION_IA=1): revisa los textos dudosos de la crónica y los reels.
"""
import json
import re
import unicodedata
from . import config


def _norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# Lista base ampliable. Se compara sin tildes y por palabra completa.
PROHIBIDO = {
    "odio_o_insulto_grave": ["subnormal", "retrasado", "maricon", "sudaca", "negrata", "puta", "zorra", "nazi", "hitler"],
    "violencia_explicita": ["degollar", "decapitar", "violar", "violacion", "tortura", "torturar", "masacre", "genocidio", "suicidio", "suicidarse"],
    "sexual": ["follar", "desnuda", "desnudo", "porno"],
    "politica_real": ["psoe", "pp", "vox", "podemos", "sumar", "ciudadanos", "erc", "junts", "bildu", "pnv", "bng",
                      "sanchez", "feijoo", "abascal", "trump", "biden", "putin", "franco", "comunismo", "capitalismo",
                      "socialismo", "marx"],
}
_PATRONES = {cat: re.compile(r"\b(" + "|".join(map(re.escape, pal)) + r")\b") for cat, pal in PROHIBIDO.items()}


def revisar(texto):
    """Devuelve (texto_publicable, lista_de_motivos)."""
    if not texto:
        return texto, []
    n = _norm(texto)
    motivos = [cat for cat, pat in _PATRONES.items() if pat.search(n)]
    return ("[…]" if motivos else texto), motivos


def registrar(sim, agente, campo, texto, motivos):
    """Guarda el original retenido para que se pueda revisar."""
    sim.bd.execute("CREATE TABLE IF NOT EXISTS moderacion(mundo TEXT, dia INT, lado TEXT, agente TEXT, campo TEXT, original TEXT, motivos TEXT)")
    sim.bd.execute("INSERT INTO moderacion VALUES(?,?,?,?,?,?,?)",
                   (sim.nombre, sim.dia, agente.lado if agente else "", agente.nombre if agente else "", campo, texto,
                    json.dumps(motivos, ensure_ascii=False)))
    sim.incidentes_moderacion = getattr(sim, "incidentes_moderacion", 0) + 1


def publicable(sim, agente, campo, texto):
    """Filtra un texto para publicarlo y registra el incidente si hace falta."""
    limpio, motivos = revisar(texto)
    if motivos:
        registrar(sim, agente, campo, texto, motivos)
    return limpio, motivos


def revisar_con_ia(texto, llamar_llm):
    """Segunda capa opcional para textos que van a publicarse en redes (crónica, guiones de reels)."""
    if not config.MODERACION_IA or not texto:
        return True, ""
    from .cerebro import llamar_json
    d = llamar_json([
        {"role": "system", "content": "Eres moderador de contenido para TikTok, Instagram y YouTube. Neutral y estricto."},
        {"role": "user", "content": "¿Este texto se puede publicar sin infringir normas de comunidad (odio, violencia gráfica, "
         "contenido sexual, acoso) y sin parecer propaganda de un partido real? Responde SOLO JSON "
         '{"publicable": true/false, "motivo": "..."}\n\nTEXTO: ' + texto}],
        modelo=config.LLM_MODELO, max_tokens=80, temperatura=0)
    return bool(d.get("publicable")), d.get("motivo", "")
