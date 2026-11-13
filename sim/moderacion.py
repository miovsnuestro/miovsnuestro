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
    "politica_real": ["psoe", "erc", "junts", "bildu", "pnv", "bng", "feijoo", "abascal", "trump", "biden", "putin",
                      "comunismo", "capitalismo", "socialismo", "marx"],
}
_PATRONES = {cat: re.compile(r"\b(" + "|".join(map(re.escape, pal)) + r")\b") for cat, pal in PROHIBIDO.items()}

# Nombres de partidos o políticos que también son palabras corrientes («podemos compartir», «sumar fuerzas»,
# «un trato franco»). Solo cuentan si se escriben como nombre propio (mayúscula en mitad de frase, o todo en
# mayúsculas) o si van junto a vocabulario político real.
AMBIGUAS_POLITICA = ["podemos", "sumar", "ciudadanos", "vox", "pp", "franco", "sanchez"]
_AMBIGUAS = re.compile(r"\b(" + "|".join(AMBIGUAS_POLITICA) + r")\b")
_CONTEXTO_POLITICO = re.compile(r"\b(partido|partidos|votar|voto|votos|votan|elecciones|electoral|congreso|diputad[oa]s?|"
                                r"gobierno|ministr[oa]|presidente|izquierda|derecha|dictador|dictadura|franquismo|franquista|lider)\b")
_INICIO_FRASE = re.compile(r"(^|[.!?¿¡:;«\"“(\n—-])\s*$")


def _norm_alineado(t):
    """Como _norm, pero con una letra por cada letra del texto, para poder volver al original."""
    sal = []
    for c in t:
        base = [x for x in unicodedata.normalize("NFD", c.lower()) if unicodedata.category(x) != "Mn"]
        sal.append(base[0] if len(base) == 1 else c)
    return "".join(sal)


def _ambigua_politica(texto):
    """True si una palabra ambigua aparece claramente como nombre de partido o de político real."""
    texto = unicodedata.normalize("NFC", texto)
    n = _norm_alineado(texto)
    for m in _AMBIGUAS.finditer(n):
        original = texto[m.start():m.end()]
        if original.isupper() and len(original) >= 2:
            return True
        if original[:1].isupper() and not _INICIO_FRASE.search(texto[:m.start()]):
            return True
        if _CONTEXTO_POLITICO.search(n[max(0, m.start() - 60):m.end() + 60]):
            return True
    return False


def revisar(texto, estricto=False):
    """Devuelve (texto_publicable, lista_de_motivos).

    estricto=True (preguntas del público): las palabras ambiguas cuentan siempre, como antes, porque ahí sí
    puede haber alguien intentando meter la política real."""
    if not texto:
        return texto, []
    n = _norm(texto)
    motivos = [cat for cat, pat in _PATRONES.items() if pat.search(n)]
    if "politica_real" not in motivos and (estricto and _AMBIGUAS.search(n) or _ambigua_politica(texto)):
        motivos.append("politica_real")
    return ("[…]" if motivos else texto), motivos


def registrar(sim, agente, campo, texto, motivos):
    """Guarda el original retenido para que se pueda revisar."""
    sim.bd.execute("CREATE TABLE IF NOT EXISTS moderacion(mundo TEXT, dia INT, lado TEXT, agente TEXT, campo TEXT, original TEXT, motivos TEXT)")
    nombre = agente.nombre if agente else ""
    # El mismo texto del mismo habitante (p. ej. unas creencias que no cambian) se registra una sola vez,
    # aunque la ficha se publique varias veces al día y durante días.
    if sim.bd.execute("SELECT 1 FROM moderacion WHERE mundo=? AND agente=? AND campo=? AND original=? LIMIT 1",
                      (sim.nombre, nombre, campo, texto)).fetchone():
        return
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
